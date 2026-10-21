# Nissan Leaf OBD BLE — Home Assistant Custom Integration

A Home Assistant custom integration for monitoring Nissan Leaf battery and
vehicle data via a Bluetooth Low Energy ELM327 OBD-II adapter (e.g. LeLink2).

This integration is a fork of
[pbutterworth/nissan-leaf-obd-ble](https://github.com/pbutterworth/nissan-leaf-obd-ble)
with the following additions:

| Feature | Original | This fork |
|---|---|---|
| OBD adapter selection | Manual MAC entry | **Dropdown of discovered adapters** |
| Generation support | Manual overrides.yaml | **Built-in per-generation profiles** |
| ZE0/AZE0 odometer | Active query (unreliable) | **Passive CAN broadcast (0x5C5)** |
| ZE0/AZE0 battery decoder | ZE1 offsets (incorrect) | **Correct ZE0 byte offsets** |
| Sensor list | Fixed (all sensors always created) | **Trimmed to generation-supported set** |
| Data persistence | Lost on HA restart | **Persisted to HA storage** |

---

## Supported hardware

| Item | Notes |
|---|---|
| LeLink2 ELM327 BLE OBD-II adapter | Primary tested hardware |
| Any ELM327 BLE OBD-II adapter advertising as `OBDBLE` | Should work; UUIDs configurable |
| ESPHome Bluetooth Proxy (e.g. GL-iNet GL-S10) | Recommended for garage setups |

## Supported vehicles

| Generation | Years | Notes |
|---|---|---|
| ZE0 | 2010–2017 | Odometer via passive CAN broadcast; ZE0 battery decoder |
| AZE0 | 2017–2018 | Same as ZE0 profile |
| ZE1 | 2018+ | Active KWP2000 odometer; includes e-Pedal sensor |
| Auto | All | All sensors enabled; uses ZE1 decoders (ZE0/AZE0 owners should pick their generation for accurate battery data) |

---

## Prerequisites

The OBD/ELM327 library (derived from
[pbutterworth/py-nissan-leaf-obd-ble](https://github.com/pbutterworth/py-nissan-leaf-obd-ble))
is bundled inside the integration as `py_nissan_leaf_obd_ble/`, so no separate
package install is needed.  The only external requirement is
`bleak-retry-connector`, which Home Assistant installs automatically, along
with the built-in `bluetooth_adapters` dependency.

---

## Installation

### Option 1 — HACS (Custom Repository)

1. Open HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/hucknz/ha_nissan_leaf_obd_ble` with category **Integration**.
3. Find *Nissan Leaf OBD BLE* and click **Download**.
4. Restart Home Assistant.

### Option 2 — Manual

1. Copy the `custom_components/ha_nissan_leaf_obd_ble/` folder into your HA
   `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Setup

1. Plug the OBD adapter into the Nissan Leaf's OBD-II port and turn on the
   ignition (or accessory mode).
2. In Home Assistant: **Settings → Devices & Services → Add Integration →
   Nissan Leaf OBD BLE**.
3. **Step 1 — OBD adapter**: Select your adapter from the dropdown.  If it
   doesn't appear, check that it's powered and within BLE range.
4. **Step 2 — Leaf generation**: Select your Leaf platform.

   | Label | Choose if… |
   |---|---|
   | ZE0 — 2010–2017 | Your Leaf is a pre-facelift (original) model |
   | AZE0 — 2017–2018 | Your Leaf is the 2017 or 2018 refresh |
   | ZE1 — 2018+ | Your Leaf is the second-generation (40 kWh / 62 kWh) |
   | Auto | You're unsure — all sensors enabled, ZE1 decoders used |

5. **Step 3 — Battery size**: Select your battery size (24, 30, 40 or 62 kWh).
   This is used to calculate state of health.
6. HA will create the device and all generation-appropriate sensor entities.
   BLE UUIDs use the LeLink2 defaults and can be changed later under
   **Configure**.

---

## Sensors

### All generations

| Entity | Unit | Description |
|---|---|---|
Entity IDs are derived from the sensor name prefixed with
`Nissan Leaf OBD BLE`, e.g. `sensor.nissan_leaf_obd_ble_state_of_charge`.

### All generations

| Sensor name | Unit | Description |
|---|---|---|
| State of charge | % | Battery charge level |
| State of health | % | Calculated from capacity and the selected battery size |
| HV battery health index | % | Health index (Hx) reported by the battery controller |
| HV battery capacity | Ah | Battery capacity |
| HV battery voltage | V | HV battery pack voltage |
| HV battery current 1 / 2 | A | Pack current (two channels) |
| Odometer | km | Total distance travelled |
| Range remaining | km | Estimated remaining range |
| Vehicle speed | km/h | Vehicle speed |
| Traction motor power | W | Traction motor power |
| Gear position | — | Park / Reverse / Neutral / Drive / Eco |
| Charging mode | — | Charge mode |
| Plug state | — | Plug state |
| Motor RPM | RPM | Motor speed |
| 12V battery voltage / current | V / A | 12V auxiliary battery |
| Number of quick charges | — | Quick (CHAdeMO) charge count |
| Number of L1/L2 charges | — | L1/L2 charge count |
| AC system power | W | Climate system power |
| AC on | — | Climate on/off |
| Estimated AC power | W | Estimated climate draw |
| Estimated PTC power | W | Estimated PTC heater draw |
| Auxiliary equipment power | W | Auxiliary equipment power |
| On-board charger output power | W | On-board charger output |
| ECO mode | — | ECO mode active |
| Rear heater | — | Rear heater active |
| Power switch | — | Power switch status |
| Tyre pressure (FR / FL / RR / RL) | kPa | Four tyre pressure sensors |

### ZE0 / AZE0 only

| Sensor name | Unit | Description |
|---|---|---|
| Battery temperature | °C | Battery temperature |

### ZE1 and Auto only

| Sensor name | Description |
|---|---|
| e-Pedal mode | e-Pedal mode active |

---

## Notes on ZE0/AZE0 battery data accuracy

The battery decoder byte offsets for ZE0/AZE0 (`state_of_charge`,
`hv_battery_health`, `hv_battery_Ah`) are based on community research and
testing on a 2016 Nissan Leaf.  They have not been exhaustively verified across
all ZE0 and AZE0 vehicles.  If you notice incorrect battery figures, please
open an issue with your raw LBC data.

---

## Configuration options

After setup, click **Configure** on the integration card to adjust:

| Option | Default | Description |
|---|---|---|
| Battery size | 30 kWh | Used to calculate state of health |
| Fast poll interval | 10 s | Polling rate when the car is on and in range |
| Slow poll interval | 300 s | Polling rate when in range but car is off |
| Extra-slow poll interval | 3600 s | Polling rate when out of BLE range |
| BLE service UUID | `0000ffe0-…` | GATT service UUID for the adapter |
| BLE read characteristic UUID | `0000ffe1-…` | Read characteristic UUID |
| BLE write characteristic UUID | `0000ffe1-…` | Write characteristic UUID |

---

## Data persistence

Sensor values are saved to HA's `.storage/` directory after each successful
poll.  After a Home Assistant restart, all sensors immediately display their
last known values — no need to drive the car home first.

---

## Troubleshooting

**No adapters appear in the dropdown**
: Ensure the OBD adapter is plugged in, the ignition is on, and the adapter
is within Bluetooth range of your HA host or a Bluetooth proxy.  Check
*Settings → Devices & Services → Bluetooth* to verify HA can see the adapter.

**Sensors stay at last known value indefinitely**
: This is the persistence feature working as designed.  Values update the
next time the car is in range and the ignition is on.

**Incorrect battery / SoC values on a ZE0 or AZE0**
: Ensure you selected the correct generation during setup.  If you used
*Auto*, re-add the integration and select *ZE0* or *AZE0* explicitly.

**Enable debug logging**
```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.ha_nissan_leaf_obd_ble: debug
```

---

## Credits

- [pbutterworth/nissan-leaf-obd-ble](https://github.com/pbutterworth/nissan-leaf-obd-ble) — original integration
- [pbutterworth/py-nissan-leaf-obd-ble](https://github.com/pbutterworth/py-nissan-leaf-obd-ble) — upstream Python library, bundled here in modified form
- [HA Community thread](https://community.home-assistant.io/t/custom-component-nissan-leaf-via-lelink-2-elm327-ble/561961)

## License

GPL-2.0-or-later (inherited from python-OBD lineage).
