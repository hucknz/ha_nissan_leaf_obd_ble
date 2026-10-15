"""Part of python-OBD (a derivative of pyOBD)."""

########################################################################
#                                                                      #
# python-OBD: A python OBD-II serial module derived from pyobd         #
#                                                                      #
# Copyright 2004 Donour Sizemore (donour@uchicago.edu)                 #
# Copyright 2009 Secons Ltd. (www.obdtester.com)                       #
# Copyright 2009 Peter J. Creath                                       #
# Copyright 2016 Brendan Whitfield (brendan-w.com)                     #
#                                                                      #
########################################################################
#                                                                      #
# decoders.py                                                          #
#                                                                      #
# This file is part of python-OBD (a derivative of pyOBD)              #
#                                                                      #
# python-OBD is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by #
# the Free Software Foundation, either version 2 of the License, or    #
# (at your option) any later version.                                  #
#                                                                      #
# python-OBD is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of       #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
# GNU General Public License for more details.                         #
#                                                                      #
# You should have received a copy of the GNU General Public License    #
# along with python-OBD.  If not, see <http://www.gnu.org/licenses/>.  #
#                                                                      #
########################################################################

import logging
import struct

from .codes import OBD_COMPLIANCE

logger = logging.getLogger(__name__)

"""
All decoders take the form:

def <name>(<list_of_messages>):
    ...
    return <value>

"""


# Special decoders
# Return objects, lists, etc


def obd_compliance(messages):
    """Decode OBD compliance."""
    d = messages[0].data[2:]
    i = d[0]

    v = None

    if i < len(OBD_COMPLIANCE):
        v = OBD_COMPLIANCE[i]
    else:
        logger.debug("Invalid response for OBD compliance (no table entry)")

    return v


def unknown(messages):
    """Decode unknown messages."""
    return None


def power_switch(messages):
    """Decode power switch messages."""
    d = messages[0].data  # only operate on a single message
    v = (d[3] & 0x80) == 0x80
    return {"power_switch": v}


def gear_position(messages):
    """Decode gear position messages."""
    d = messages[0].data  # only operate on a single message
    match d[3]:
        case 1:
            v = "Park"
        case 2:
            v = "Reverse"
        case 3:
            v = "Neutral"
        case 4:
            v = "Drive"
        case 5:
            v = "Eco"
        case _:
            v = "Unknown"

    return {"gear_position": v}


def bat_12v_voltage(messages):
    """Decode 12V battery voltage messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 0.08
    return {"bat_12v_voltage": v}


def bat_12v_current(messages):
    """Decode 12V battery current messages."""
    d = messages[0].data  # only operate on a single message
    v = struct.unpack("!h", d[3:5])[0] / 256
    return {"bat_12v_current": v}


def quick_charges(messages):
    """Decode Number of quick charges messages."""
    d = messages[0].data  # only operate on a single message
    v = int.from_bytes(d[3:5])
    return {"quick_charges": v}


def l1_l2_charges(messages):
    """Decode Number of L1/L2 charges messages."""
    d = messages[0].data  # only operate on a single message
    v = int.from_bytes(d[3:5])
    return {"l1_l2_charges": v}


def ambient_temp(messages):
    """Decode battery/ambient temperature messages.
    
    Note: On AZE0 this reads battery temperature. The value 0xFF (87.5°C)
    is an error/uninitialized state and should be filtered by the sensor platform.
    """
    d = messages[0].data  # only operate on a single message
    raw = d[3]
    # Filter out error values (0xFF typically indicates no valid data)
    if raw == 0xFF:
        return {"ambient_temp": None}
    v = raw / 2 - 40
    return {"ambient_temp": v}


def estimated_ac_power(messages):
    """Decode estimated AC power messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 50
    return {"estimated_ac_power": v}


def estimated_ptc_power(messages):
    """Decode estimated PTC power messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 250
    return {"estimated_ptc_power": v}


def aux_power(messages):
    """Decode Auxiliary equipment power messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 100
    return {"aux_power": v}


def ac_power(messages):
    """Decode AC system power messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 250
    return {"ac_power": v}


def plug_state(messages):
    """Decode Plug state of J1772 socket messages."""
    d = messages[0].data  # only operate on a single message
    match d[3]:
        case 0:
            v = "Not plugged"
        case 1:
            v = "Partial plugged"
        case 2:
            v = "Plugged"
        case _:
            v = "Unknown"
    return {"plug_state": v}


def charge_mode(messages):
    """Decode Charging mode messages."""
    d = messages[0].data  # only operate on a single message
    match d[3]:
        case 0:
            v = "Not charging"
        case 1:
            v = "L1 charging"
        case 2:
            v = "L2 charging"
        case 3:
            v = "L3 charging"
        case _:
            v = "Unknown"
    return {"charge_mode": v}


def rpm(messages):
    """Decode Motor RPM messages."""
    d = messages[0].data  # only operate on a single message
    v = struct.unpack("!h", d[3:5])[0]
    # todo: fix this parser
    return {"rpm": v}


def obc_out_power(messages):
    """Decode On-board charger output power messages (W)."""
    d = messages[0].data  # only operate on a single message
    v = struct.unpack("!h", d[3:5])[0] * 100
    return {"obc_out_power": v}


def motor_power(messages):
    """Decode Traction motor power messages (W)."""
    d = messages[0].data  # only operate on a single message
    v = struct.unpack("!h", d[3:5])[0] * 40
    return {"motor_power": v}


def speed(messages):
    """Decode Vehicle speed messages (km/h)."""
    d = messages[0].data  # only operate on a single message
    v = struct.unpack("!h", d[3:5])[0] / 10
    return {"speed": v}


def ac_on(messages):
    """Decode AC status messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] == 0x01
    return {"ac_on": v}


def rear_heater(messages):
    """Decode Rear heater status messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] == 0xA2
    return {"rear_heater": v}


def eco_mode(messages):
    """Decode ECO mode status messages."""
    d = messages[0].data  # only operate on a single message
    v = (d[3] == 0x10) or (d[3] == 0x11)
    return {"eco_mode": v}


def e_pedal_mode(messages):
    """Decode e-Pedal mode status messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] == 0x04
    return {"e_pedal_mode": v}


def odometer(messages):
    """Decode Total odometer reading (km) from KWP2000 diagnostic session.
    
    Response from CAR-CAN ECU at 0x743 via ReadDataByLocalIdentifier (service 0x21).
    ISO 15765-4 first frame format: [0x6N] [length] [padding] [odometer...]
    Odometer is a 4-byte big-endian unsigned integer.
    Example: 61 01 00 00 00 00 00 00 00 01 57 2c where bytes[8:12] = 0x0001572c = 87,852 km.
    
    Verified on 2016 Nissan Leaf (active polling, on-demand read).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # For multi-frame ISO 15765-4 responses
    d = messages[0].data if messages else bytes()
    
    logger.debug(f"odometer: Full data ({len(d)} bytes): {d.hex() if d else '(empty)'}")
    
    if len(d) < 4:
        logger.warning(f"odometer: Insufficient data ({len(d)} bytes)")
        return None

    # KWP negative response: 0x7F, requested service, error code.
    if d[0] == 0x7F:
        return None
    
    v = None
    # Detect frame type and extract odometer from correct position
    if len(d) >= 12 and d[0] == 0x61:
        # ISO 15765-4 first frame (0x61 = frame type)
        # Structure: [0x61] [length_byte] [padding...] [odometer @ byte 8]
        logger.debug("odometer: ISO 15765-4 first frame detected")
        v = int.from_bytes(d[8:12], byteorder="big", signed=False)
        logger.debug(f"odometer: Reading from [8:12] = {d[8:12].hex()} = {v} km")
    
    # Standard KWP2000 response: [0x60=service] [odometer...]
    elif len(d) >= 5 and d[0] == 0x60:
        v = int.from_bytes(d[1:5], byteorder="big", signed=False)
        logger.debug(f"odometer: KWP2000 format [1:5] = {d[1:5].hex()} = {v} km")
    
    # Fallback: try reading 4 bytes from start
    elif len(d) >= 4:
        v = int.from_bytes(d[0:4], byteorder="big", signed=False)
        logger.debug(f"odometer: Fallback format [0:4] = {d[0:4].hex()} = {v} km")

    if v is not None and 0 < v < 10_000_000:
        return {"odometer": v}
    
    return None


def tp_fr(messages):
    """Decode Tyre pressure front right (kPa) messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 1.7236894
    return {"tp_fr": v}


def tp_fl(messages):
    """Decode Tyre pressure front left (kPa) messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 1.7236894
    return {"tp_fl": v}


def tp_rr(messages):
    """Decode Tyre pressure rear right (kPa) messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 1.7236894
    return {"tp_rr": v}


def tp_rl(messages):
    """Decode Tyre pressure rear left (kPa) messages."""
    d = messages[0].data  # only operate on a single message
    v = d[3] * 1.7236894
    return {"tp_rl": v}


def range_remaining(messages):
    """Decode Remaining range (km) messages."""
    # todo: fix this decoder
    d = messages[0].data  # only operate on a single message
    v = struct.unpack("!h", d[3:5])[0] / 10
    return {"range_remaining": v}


def lbc(messages):
    """Decode LBC message (ZE1 generation, 2018+).
    
    Returns the Health Index (Hx), not State of Health (SOH). For ZE0/AZE0 
    (2010-2018), the integration uses custom byte offsets via the generations.py 
    override system.
    """
    d = messages[0].data
    if len(d) == 0:
        return None
    hv_battery_current_1 = int.from_bytes(d[2:6], byteorder="big", signed=False)
    hv_battery_current_2 = int.from_bytes(d[8:12], byteorder="big", signed=False)
    if (hv_battery_current_1 & 0x8000000) == 0x8000000:
        hv_battery_current_1 = hv_battery_current_1 | -0x100000000
    if (hv_battery_current_2 & 0x8000000) == 0x8000000:
        hv_battery_current_2 = hv_battery_current_2 | -0x100000000
    return {
        "state_of_charge": int.from_bytes(d[33:36]) / 10000,
        "hv_battery_health": int.from_bytes(d[30:32]) / 102.4,
        "hv_battery_Ah": int.from_bytes(d[37:40]) / 10000,
        "hv_battery_current_1": hv_battery_current_1 / 1024,
        "hv_battery_current_2": hv_battery_current_2 / 1024,
        "hv_battery_voltage": int.from_bytes(d[20:22]) / 100,
    }

# Decoders for CAN broadcast messages (multiple messages may be passed in, but only the first is used) to support ZE0/AZE0 generations
def odometer_can_broadcast(messages):
    """Decode odometer from CAN broadcast 0x5C5 (ZE0/AZE0 generations).
    
    Odometer is a 3-byte big-endian value at payload offset 1-3.
    Verified working on 2016 Nissan Leaf with 87786->87787 transition.
    """
    if not messages or not messages[0].data or len(messages[0].data) < 4:
        return None
    d = messages[0].data  # 8-byte raw CAN frame
    v = int.from_bytes(d[1:4], byteorder='big', signed=False)
    if 0 < v < 10_000_000:
        return {"odometer": v}
    return None