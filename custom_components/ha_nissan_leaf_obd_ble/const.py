"""Constants for Nissan Leaf OBD BLE (ha_nissan_leaf_obd_ble)."""

NAME = "Nissan Leaf OBD BLE"
DOMAIN = "ha_nissan_leaf_obd_ble"
VERSION = "1.0.1"

ISSUE_URL = "https://github.com/hucknz/ha_nissan_leaf_obd_ble/issues"

# Configuration keys — stored in config entry DATA (require re-adding to change)
CONF_GENERATION = "generation"

# Configuration keys — stored in config entry OPTIONS (changeable via Configure)
CONF_SERVICE_UUID = "service_uuid"
CONF_CHARACTERISTIC_UUID_READ = "characteristic_uuid_read"
CONF_CHARACTERISTIC_UUID_WRITE = "characteristic_uuid_write"
CONF_NOMINAL_AH = "nominal_ah"

# Default BLE UUIDs (LeLink2 / OBDBLE dongle)
DEFAULT_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_READ = "0000ffe1-0000-1000-8000-00805f9b34fb"
DEFAULT_CHARACTERISTIC_UUID_WRITE = "0000ffe1-0000-1000-8000-00805f9b34fb"

# BLE local names to search for when scanning for adapters
BLE_LOCAL_NAMES = {"OBDBLE", "Android-Vlink", "Vgate iCar Pro"}

# Generation identifiers
GENERATION_AUTO = "auto"
GENERATION_ZE0 = "ze0"
GENERATION_AZE0 = "aze0"
GENERATION_ZE1 = "ze1"

# Human-readable labels for UI display
GENERATION_OPTIONS: dict[str, str] = {
    GENERATION_ZE0: "ZE0 — 2010–2017 Nissan Leaf (uses passive CAN odometer)",
    GENERATION_AZE0: "AZE0 — 2017–2018 Nissan Leaf (uses passive CAN odometer)",
    GENERATION_ZE1: "ZE1 — 2018+ Nissan Leaf",
    GENERATION_AUTO: "Auto — all generations (recommended if unsure)",
}

# Battery nominal Ah capacity by size (used to calculate State of Health)
# These are the approximate maximum usable capacities for each battery size.
BATTERY_NOMINAL_AH: dict[int, float] = {
    24: 60.6,
    30: 79.48,
    40: 105.6,
    62: 167.6,
}

# Default nominal Ah if user doesn't specify (30 kWh is most common)
DEFAULT_NOMINAL_AH = 79.48

# Default polling intervals (seconds)
DEFAULT_FAST_POLL = 10
DEFAULT_SLOW_POLL = 300
DEFAULT_XS_POLL = 3600
DEFAULT_FETCH_TIMEOUT = 90

# Storage — persists last-known sensor values across HA restarts
STORAGE_KEY = f"{DOMAIN}.sensor_cache"
STORAGE_VERSION = 1

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
Custom integration — report issues at: {ISSUE_URL}
-------------------------------------------------------------------
"""
