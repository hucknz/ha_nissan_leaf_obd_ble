"""API for nissan leaf obd ble."""

# import asyncio
import logging

from bleak.backends.device import BLEDevice

from .obd import OBD
from .profiles import get_generation_commands, VALID_GENERATIONS, DEFAULT_GENERATION

_LOGGER: logging.Logger = logging.getLogger(__package__)


class NissanLeafObdBleApiClient:
    """API for connecting to the Nissan Leaf OBD BLE dongle."""

    def __init__(
        self,
        ble_device: BLEDevice,
    ) -> None:
        """Initialise."""
        self._ble_device = ble_device

    async def async_get_data(
        self,
        options=None,
        generation: str = DEFAULT_GENERATION,
        extra_commands: dict | None = None,
        disabled_commands: set[str] | None = None,
    ) -> dict | None:
        """Get data from the API.
        
        Args:
            options: BLE connection options (service_uuid, characteristic_uuid_read, characteristic_uuid_write)
            generation: Nissan Leaf generation profile. Options:
                - 'auto' (default): Automatic mode, includes both active and passive odometer sources.
                  Recommended for maximum compatibility. ZE0/AZE0 users get working passive odometer,
                  ZE1 users get fast active odometer (passive is redundant but harmless).
                - 'ze0': Optimized for 2010-2017 Leaf (passive odometer only)
                - 'aze0': Optimized for 2017-2018 Leaf (passive odometer only)  
                - 'ze1': Optimized for 2018+ Leaf (active odometer only)
            extra_commands: dict of command overrides to merge with generation defaults
            disabled_commands: set of command names to skip
            
        Returns:
            dict of sensor readings, or None if connection fails
            
        Raises:
            ValueError: if generation is not recognized
        """

        if self._ble_device is None:
            return {}
        
        # Validate and retrieve generation-specific command table
        if generation not in VALID_GENERATIONS:
            raise ValueError(
                f"Unknown generation '{generation}'. "
                f"Valid options: {', '.join(sorted(VALID_GENERATIONS))}"
            )

        opts = options or {}
        service_uuid = opts.get("service_uuid")
        characteristic_uuid_read = opts.get("characteristic_uuid_read")
        characteristic_uuid_write = opts.get("characteristic_uuid_write")

        api = await OBD.create(
            self._ble_device,
            protocol="6",
            service_uuid=service_uuid,
            characteristic_uuid_read=characteristic_uuid_read,
            characteristic_uuid_write=characteristic_uuid_write,
        )

        if api is None:
            return None

        try:
            # Get generation-specific command table with user overrides applied
            commands = get_generation_commands(
                generation,
                extra_commands=extra_commands,
                disabled_commands=disabled_commands,
            )
            
            data = {}
            _broke_early = False
            for command in commands.values():
                response = await api.query(command, force=True)
                # the first command is the Mystery command. If this doesn't have a response, then none of the other will
                if command.name == "unknown" and len(response.messages) == 0:
                    _broke_early = True
                    break
            if _broke_early:
                # The first Mystery (0210C0) wakes the CAN bus; the ECU is usually not yet
                # responsive for that same query (pbutterworth PR #14). Reconnect after a settle
                # and retry the whole sweep; the fresh init takes ~10 s by which the ECU answers.
                _LOGGER.debug("Mystery returned no data; reconnecting and retrying after CAN wake")
                import asyncio
                await asyncio.sleep(10)
                api2 = await OBD.create(
                    self._ble_device,
                    protocol="6",
                    service_uuid=service_uuid,
                    characteristic_uuid_read=characteristic_uuid_read,
                    characteristic_uuid_write=characteristic_uuid_write,
                )
                if api2 is None:
                    return data
                try:
                    data = {}
                    for command in commands.values():
                        r2 = await api2.query(command, force=True)
                        if r2.value is not None:
                            data.update(r2.value)
                finally:
                    await api2.close()
                return data
                if response.value is not None:
                    data.update(response.value)  # send the command, and parse the response
            _LOGGER.debug("Returning data: %s", data)
            return data
        finally:
            await api.close()

