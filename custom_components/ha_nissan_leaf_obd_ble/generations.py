"""Generation-specific sensor descriptions and LBC decoder overrides.

Each Nissan Leaf generation uses slightly different byte offsets in the LBC
(Lithium-ion Battery Controller) response and different odometer retrieval
methods.  This module encodes those differences so the coordinator and sensor
platform can configure themselves correctly for the selected generation without
requiring the user to write manual overrides.

ZE0 / AZE0 (2010–2018):
  - Odometer via passive CAN broadcast (frame 0x5C5) — active KWP2000 query
    is disabled because it is unreliable on these ECUs.
  - LBC response byte offsets differ from the ZE1 platform.
  - e-Pedal mode did not exist on these generations.

ZE1 (2018+):
  - Odometer via active KWP2000 diagnostic session.
  - LBC uses the library's default decoder (ZE1 offsets).
  - e-Pedal mode is available.

Auto:
  - Both odometer commands are active; whichever returns data wins.
  - Uses the ZE1 LBC decoder as default.  ZE0/AZE0 owners should select
    their generation explicitly for accurate battery data.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)

from .const import (
    GENERATION_AUTO,
    GENERATION_AZE0,
    GENERATION_ZE0,
    GENERATION_ZE1,
)

_LOGGER = logging.getLogger(__name__)


def _decode_signed_28bit(raw: int) -> int:
    """Decode a signed 28-bit value stored in a four-byte field."""
    raw &= 0x0FFFFFFF
    return raw - 0x10000000 if raw & 0x08000000 else raw


# ---------------------------------------------------------------------------
# LBC decoders
# ---------------------------------------------------------------------------


def _make_lbc_decoder_ze0(nominal_ah: float):
    """Create an LBC decoder for ZE0/AZE0 that includes SOH calculation.
    
    Args:
        nominal_ah: The nominal (maximum) Ah capacity of the battery.
    
    Returns:
        A decoder function that returns both battery metrics and calculated SOH.
    """
    def decoder(messages):
        d = messages[0].data
        if not d:
            return None

        raw1 = int.from_bytes(d[2:6], byteorder="big", signed=False)
        raw2 = int.from_bytes(d[8:12], byteorder="big", signed=False)

        raw1 = _decode_signed_28bit(raw1)
        raw2 = _decode_signed_28bit(raw2)

        current_ah = int.from_bytes(d[34:38], byteorder="big") / 10000
        soh = (current_ah / nominal_ah) * 100 if nominal_ah > 0 else None

        return {
            "state_of_charge": int.from_bytes(d[30:34], byteorder="big") / 10000,
            "hv_battery_health": int.from_bytes(d[28:30], byteorder="big") / 102.4,
            "hv_battery_Ah": current_ah,
            "state_of_health": soh,
            "hv_battery_current_1": raw1 / 1024,
            "hv_battery_current_2": raw2 / 1024,
            "hv_battery_voltage": int.from_bytes(d[20:22], byteorder="big") / 100,
        }
    return decoder


def _lbc_decoder_ze0(messages):
    """Decode LBC response for ZE0/AZE0 generation (2010–2018 Nissan Leaf).

    Byte offsets verified against LeafSpy on a 2018 AZE0 Nissan Leaf
    (30 kWh, 88,040 km).
    
    Note: hv_battery_health returns the Health Index (Hx), not State of Health (SOH).
    Hx is a normalized battery condition metric. SOH must be calculated separately
    using the nominal battery Ah capacity.
    """
    d = messages[0].data
    if not d:
        return None

    raw1 = int.from_bytes(d[2:6], byteorder="big", signed=False)
    raw2 = int.from_bytes(d[8:12], byteorder="big", signed=False)

    raw1 = _decode_signed_28bit(raw1)
    raw2 = _decode_signed_28bit(raw2)

    return {
        "state_of_charge": int.from_bytes(d[30:34], byteorder="big") / 10000,
        "hv_battery_health": int.from_bytes(d[28:30], byteorder="big") / 102.4,
        "hv_battery_Ah": int.from_bytes(d[34:38], byteorder="big") / 10000,
        "hv_battery_current_1": raw1 / 1024,
        "hv_battery_current_2": raw2 / 1024,
        "hv_battery_voltage": int.from_bytes(d[20:22], byteorder="big") / 100,
    }


def _make_soh_decoder_ze0(nominal_ah: float):
    """Create a SOH decoder for ZE0/AZE0 that uses the nominal Ah capacity.
    
    SOH (State of Health) = current Ah / nominal Ah * 100%
    
    Args:
        nominal_ah: The nominal (maximum) Ah capacity of the battery.
    
    Returns:
        A decoder function that returns {"state_of_health": soh_percent}
    """
    def decoder(messages):
        d = messages[0].data
        if not d:
            return None
        current_ah = int.from_bytes(d[34:38], byteorder="big") / 10000
        soh = (current_ah / nominal_ah) * 100 if nominal_ah > 0 else None
        return {"state_of_health": soh}
    return decoder


def _make_lbc_decoder_ze1(nominal_ah: float):
    """Create an LBC decoder for ZE1 that includes SOH calculation.
    
    Args:
        nominal_ah: The nominal (maximum) Ah capacity of the battery.
    
    Returns:
        A decoder function that returns both battery metrics and calculated SOH.
    """
    def decoder(messages):
        d = messages[0].data
        if not d:
            return None

        raw1 = int.from_bytes(d[2:6], byteorder="big", signed=False)
        raw2 = int.from_bytes(d[8:12], byteorder="big", signed=False)

        raw1 = _decode_signed_28bit(raw1)
        raw2 = _decode_signed_28bit(raw2)

        current_ah = int.from_bytes(d[37:40], byteorder="big") / 10000
        soh = (current_ah / nominal_ah) * 100 if nominal_ah > 0 else None

        return {
            "state_of_charge": int.from_bytes(d[33:36], byteorder="big") / 10000,
            "hv_battery_health": int.from_bytes(d[30:32], byteorder="big") / 102.4,
            "hv_battery_Ah": current_ah,
            "state_of_health": soh,
            "hv_battery_current_1": raw1 / 1024,
            "hv_battery_current_2": raw2 / 1024,
            "hv_battery_voltage": int.from_bytes(d[20:22], byteorder="big") / 100,
        }
    return decoder


def _lbc_decoder_ze1(messages):
    """Decode LBC response for ZE1 generation (2018+ Nissan Leaf).

    This mirrors the default decoder shipped with the py-nissan-leaf-obd-ble
    library. It is reproduced here so the coordinator can supply it as an
    explicit extra_command override when the 'auto' profile is in use,
    ensuring consistent behaviour regardless of the library version installed.
    
    Note: hv_battery_health returns the Health Index (Hx), not State of Health (SOH).
    SOH must be calculated separately using the nominal battery Ah capacity.
    """
    d = messages[0].data
    if not d:
        return None

    raw1 = int.from_bytes(d[2:6], byteorder="big", signed=False)
    raw2 = int.from_bytes(d[8:12], byteorder="big", signed=False)

    raw1 = _decode_signed_28bit(raw1)
    raw2 = _decode_signed_28bit(raw2)

    return {
        "state_of_charge": int.from_bytes(d[33:36], byteorder="big") / 10000,
        "hv_battery_health": int.from_bytes(d[30:32], byteorder="big") / 102.4,
        "hv_battery_Ah": int.from_bytes(d[37:40], byteorder="big") / 10000,
        "hv_battery_current_1": raw1 / 1024,
        "hv_battery_current_2": raw2 / 1024,
        "hv_battery_voltage": int.from_bytes(d[20:22], byteorder="big") / 100,
    }


def _make_soh_decoder_ze1(nominal_ah: float):
    """Create a SOH decoder for ZE1 that uses the nominal Ah capacity.
    
    SOH (State of Health) = current Ah / nominal Ah * 100%
    
    Args:
        nominal_ah: The nominal (maximum) Ah capacity of the battery.
    
    Returns:
        A decoder function that returns {"state_of_health": soh_percent}
    """
    def decoder(messages):
        d = messages[0].data
        if not d:
            return None
        current_ah = int.from_bytes(d[37:40], byteorder="big") / 10000
        soh = (current_ah / nominal_ah) * 100 if nominal_ah > 0 else None
        return {"state_of_health": soh}
    return decoder


# ---------------------------------------------------------------------------
# Sensor entity descriptions
# ---------------------------------------------------------------------------

# Complete catalogue of all possible sensors.  The generation-specific filter
# below trims this down to the subset supported by each platform.
_ALL_SENSORS: dict[str, SensorEntityDescription] = {
    "power_switch": SensorEntityDescription(
        key="power_switch",
        icon="mdi:power",
        name="Power switch",
    ),
    "gear_position": SensorEntityDescription(
        key="gear_position",
        icon="mdi:car-shift-pattern",
        name="Gear position",
        device_class=SensorDeviceClass.ENUM,
        options=["Park", "Reverse", "Neutral", "Drive", "Eco", "Unknown"],
    ),
    "bat_12v_voltage": SensorEntityDescription(
        key="bat_12v_voltage",
        icon="mdi:car-battery",
        name="12V battery voltage",
        native_unit_of_measurement="V",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "bat_12v_current": SensorEntityDescription(
        key="bat_12v_current",
        icon="mdi:car-battery",
        name="12V battery current",
        native_unit_of_measurement="A",
        suggested_display_precision=2,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "quick_charges": SensorEntityDescription(
        key="quick_charges",
        icon="mdi:ev-plug-chademo",
        name="Number of quick charges",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "l1_l2_charges": SensorEntityDescription(
        key="l1_l2_charges",
        icon="mdi:ev-plug-type2",
        name="Number of L1/L2 charges",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ambient_temp": SensorEntityDescription(
        key="ambient_temp",
        icon="mdi:thermometer",
        name="Battery temperature",
        native_unit_of_measurement="°C",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "estimated_ac_power": SensorEntityDescription(
        key="estimated_ac_power",
        icon="mdi:air-conditioner",
        name="Estimated AC power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "estimated_ptc_power": SensorEntityDescription(
        key="estimated_ptc_power",
        icon="mdi:heating-coil",
        name="Estimated PTC power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "aux_power": SensorEntityDescription(
        key="aux_power",
        icon="mdi:generator-portable",
        name="Auxiliary equipment power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ac_power": SensorEntityDescription(
        key="ac_power",
        icon="mdi:air-conditioner",
        name="AC system power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "plug_state": SensorEntityDescription(
        key="plug_state",
        icon="mdi:ev-plug-type1",
        name="Plug state",
        device_class=SensorDeviceClass.ENUM,
        options=["Not plugged", "Partial plugged", "Plugged", "Unknown"],
    ),
    "charge_mode": SensorEntityDescription(
        key="charge_mode",
        icon="mdi:ev-station",
        name="Charging mode",
        device_class=SensorDeviceClass.ENUM,
        options=["Not charging", "L1 charging", "L2 charging", "L3 charging", "Unknown"],
    ),
    "rpm": SensorEntityDescription(
        key="rpm",
        icon="mdi:gauge",
        name="Motor RPM",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "obc_out_power": SensorEntityDescription(
        key="obc_out_power",
        icon="mdi:battery-charging",
        name="On-board charger output power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "motor_power": SensorEntityDescription(
        key="motor_power",
        icon="mdi:engine",
        name="Traction motor power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "speed": SensorEntityDescription(
        key="speed",
        icon="mdi:speedometer",
        name="Vehicle speed",
        native_unit_of_measurement="km/h",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ac_on": SensorEntityDescription(
        key="ac_on",
        icon="mdi:air-conditioner",
        name="AC on",
    ),
    "rear_heater": SensorEntityDescription(
        key="rear_heater",
        icon="mdi:heating-coil",
        name="Rear heater",
    ),
    "eco_mode": SensorEntityDescription(
        key="eco_mode",
        icon="mdi:leaf",
        name="ECO mode",
    ),
    "odometer": SensorEntityDescription(
        key="odometer",
        icon="mdi:counter",
        name="Odometer",
        native_unit_of_measurement="km",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "tp_fr": SensorEntityDescription(
        key="tp_fr",
        icon="mdi:car-tire-alert",
        name="Tyre pressure — front right",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "tp_fl": SensorEntityDescription(
        key="tp_fl",
        icon="mdi:car-tire-alert",
        name="Tyre pressure — front left",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "tp_rr": SensorEntityDescription(
        key="tp_rr",
        icon="mdi:car-tire-alert",
        name="Tyre pressure — rear right",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "tp_rl": SensorEntityDescription(
        key="tp_rl",
        icon="mdi:car-tire-alert",
        name="Tyre pressure — rear left",
        native_unit_of_measurement="kPa",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "range_remaining": SensorEntityDescription(
        key="range_remaining",
        icon="mdi:map-marker-distance",
        name="Range remaining",
        native_unit_of_measurement="km",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "state_of_charge": SensorEntityDescription(
        key="state_of_charge",
        icon="mdi:battery-charging",
        name="State of charge",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "state_of_health": SensorEntityDescription(
        key="state_of_health",
        icon="mdi:battery-heart",
        name="State of health",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_health": SensorEntityDescription(
        key="hv_battery_health",
        icon="mdi:battery-heart",
        name="HV battery health index",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_Ah": SensorEntityDescription(
        key="hv_battery_Ah",
        icon="mdi:battery",
        name="HV battery capacity",
        native_unit_of_measurement="Ah",
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_current_1": SensorEntityDescription(
        key="hv_battery_current_1",
        icon="mdi:current-dc",
        name="HV battery current 1",
        native_unit_of_measurement="A",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_current_2": SensorEntityDescription(
        key="hv_battery_current_2",
        icon="mdi:current-dc",
        name="HV battery current 2",
        native_unit_of_measurement="A",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "hv_battery_voltage": SensorEntityDescription(
        key="hv_battery_voltage",
        icon="mdi:lightning-bolt",
        name="HV battery voltage",
        native_unit_of_measurement="V",
        suggested_display_precision=1,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ZE1-only
    "e_pedal_mode": SensorEntityDescription(
        key="e_pedal_mode",
        icon="mdi:foot-print",
        name="e-Pedal mode",
    ),
}

# Sensors not present on ZE0 / AZE0 platforms
_ZE0_EXCLUDED = {"e_pedal_mode"}

# Sensors not present on ZE1 / Auto platforms
_ZE1_EXCLUDED = {"ambient_temp"}

# Map from generation identifier → ordered list of sensor keys
GENERATION_SENSOR_KEYS: dict[str, list[str]] = {
    GENERATION_ZE0: [k for k in _ALL_SENSORS if k not in _ZE0_EXCLUDED],
    GENERATION_AZE0: [k for k in _ALL_SENSORS if k not in _ZE0_EXCLUDED],
    GENERATION_ZE1: [k for k in _ALL_SENSORS if k not in _ZE1_EXCLUDED],
    GENERATION_AUTO: [k for k in _ALL_SENSORS if k not in _ZE1_EXCLUDED],
}


def get_sensors_for_generation(generation: str) -> list[SensorEntityDescription]:
    """Return the sensor entity descriptions appropriate for *generation*."""
    keys = GENERATION_SENSOR_KEYS.get(generation, list(_ALL_SENSORS.keys()))
    return [_ALL_SENSORS[k] for k in keys if k in _ALL_SENSORS]


# ---------------------------------------------------------------------------
# Generation-specific OBD command overrides
# ---------------------------------------------------------------------------

def get_extra_commands_for_generation(
    generation: str, nominal_ah: float | None = None
) -> dict:
    """Return a dict of OBDCommand overrides to pass to async_get_data().

    For ZE0/AZE0 we replace the default (ZE1) LBC decoder with one that
    uses the correct byte offsets for these older platforms.
    
    For all generations, we use an LBC decoder that includes SOH calculation
    based on the provided nominal Ah capacity.

    Args:
        generation: The Leaf generation (ze0, aze0, ze1, auto).
        nominal_ah: The nominal battery capacity in Ah (used for SOH calculation).
                    Defaults to DEFAULT_NOMINAL_AH.

    Returns:
        A dict of OBDCommand overrides.
    """
    from .const import DEFAULT_NOMINAL_AH  # noqa: PLC0415

    if nominal_ah is None:
        nominal_ah = DEFAULT_NOMINAL_AH

    try:
        from .py_nissan_leaf_obd_ble.OBDCommand import OBDCommand  # noqa: PLC0415
        from .py_nissan_leaf_obd_ble.commands import leaf_commands  # noqa: PLC0415
    except ImportError:
        _LOGGER.error(
            "py_nissan_leaf_obd_ble is not installed — cannot build generation overrides"
        )
        return {}

    base_lbc = leaf_commands.get("lbc")
    if base_lbc is None:
        _LOGGER.warning("lbc command not found in leaf_commands; skipping override")
        return {}

    # Create generation-specific LBC decoder that includes SOH calculation
    if generation in (GENERATION_ZE0, GENERATION_AZE0):
        lbc_decoder = _make_lbc_decoder_ze0(nominal_ah)
    else:
        # ZE1 and AUTO both use ZE1 byte offsets
        lbc_decoder = _make_lbc_decoder_ze1(nominal_ah)

    return {
        "lbc": OBDCommand(
            "lbc",
            "Li-ion battery controller",
            base_lbc.command,
            base_lbc.bytes,
            lbc_decoder,
            header=base_lbc.header,
        )
    }
