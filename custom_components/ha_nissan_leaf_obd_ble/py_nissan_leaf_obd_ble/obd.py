"""The main API for talking to the OBD BLE module."""

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
# obd.py                                                               #
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

import asyncio
import logging

from bleak.backends.device import BLEDevice

from .elm327 import ELM327, OBDStatus
from .OBDResponse import OBDResponse
from .protocols.protocol import Frame, Message
from .utils import isHex

logger = logging.getLogger(__name__)


class OBD:
    """Class representing an OBD-II connection with it's assorted commands/sensors."""

    def __init__(
        self,
        device: BLEDevice,
        fast=True,
        timeout=0.1,
    ) -> None:
        """Initialise."""
        self.interface = None
        self.fast = fast  # global switch for disabling optimizations
        self.timeout = timeout
        self.__device = device
        self.__last_header = ()  # for comparing with the previously used header
        self.__frame_counts = {}  # keeps track of the number of return frames for each command

    @classmethod
    async def create(
        cls,
        device: BLEDevice,
        protocol=None,
        fast=True,
        timeout=0.1,
        check_voltage=True,
        start_low_power=False,
        service_uuid=None,
        characteristic_uuid_read=None,
        characteristic_uuid_write=None,
    ):
        """Manufacture instance."""
        self = cls(device, fast, timeout)

        logger.debug("Connecting to BLEDevice")
        await self.__connect(
            protocol,
            check_voltage,
            start_low_power,
            service_uuid=service_uuid,
            characteristic_uuid_read=characteristic_uuid_read,
            characteristic_uuid_write=characteristic_uuid_write,
        )
        return self

    async def __connect(
        self,
        protocol,
        check_voltage,
        start_low_power,
        service_uuid=None,
        characteristic_uuid_read=None,
        characteristic_uuid_write=None,
    ):
        """Attempt to instantiate an ELM327 connection object."""

        self.interface = await ELM327.create(
            self.__device,
            protocol,
            self.timeout,
            check_voltage,
            start_low_power,
            service_uuid=service_uuid,
            characteristic_uuid_read=characteristic_uuid_read,
            characteristic_uuid_write=characteristic_uuid_write,
        )

        # if the connection failed, close it
        if self.status() == OBDStatus.NOT_CONNECTED:
            # the ELM327 class will report its own errors
            await self.close()

    async def __set_header(self, header) -> None:
        if header == self.__last_header:
            return
        r = await self.interface.send_and_parse(b"AT SH " + header + b" ")
        if not r:
            logger.info("Set Header ('AT SH %s') did not return data", header)
            return
        if "\n".join([m.raw() for m in r]) != "OK":
            logger.info("Set Header ('AT SH %s') did not return 'OK'", header)
            return

        r = await self.interface.send_and_parse(b"AT FC SH " + header + b" ")
        if not r:
            logger.info("Set Header ('AT FC SH %s') did not return data", header)
            return
        if "\n".join([m.raw() for m in r]) != "OK":
            logger.info("Set Header ('AT FC SH %s') did not return 'OK'", header)
            return

        r = await self.interface.send_and_parse(b"AT FC SD 30 00 00")
        if not r:
            logger.info("Set Header ('AT FC SD %s') did not return data", header)
            return
        if "\n".join([m.raw() for m in r]) != "OK":
            logger.info("Set Header ('AT FC SD %s') did not return 'OK'", header)
            return

        r = await self.interface.send_and_parse(b"AT FC SM 1")
        if not r:
            logger.info("Set Header ('AT FC SM %s') did not return data", header)
            return
        if "\n".join([m.raw() for m in r]) != "OK":
            logger.info("Set Header ('AT FC SM %s') did not return 'OK'", header)
            return

        self.__last_header = header

    async def close(self):
        """Close the connection, and clears supported_commands."""

        if self.interface is not None:
            logger.info("Closing connection")
            await self.interface.close()
            self.interface = None

    def status(self):
        """Return the OBD connection status."""
        if self.interface is None:
            return OBDStatus.NOT_CONNECTED
        return self.interface.status()

    async def low_power(self):
        """Enter low power mode."""
        if self.interface is None:
            return OBDStatus.NOT_CONNECTED
        return await self.interface.low_power()

    async def normal_power(self):
        """Exit low power mode."""
        if self.interface is None:
            return OBDStatus.NOT_CONNECTED
        return await self.interface.normal_power()

    def protocol_name(self):
        """Return the name of the protocol being used by the ELM327."""
        if self.interface is None:
            return ""
        return self.interface.protocol_name()

    def protocol_id(self):
        """Return the ID of the protocol being used by the ELM327."""
        if self.interface is None:
            return ""
        return self.interface.protocol_id()

    def is_connected(self):
        """Return. a boolean for whether a connection with the car was made.

        Note: this function returns False when:
        obd.status = OBDStatus.ELM_CONNECTED
        """
        return self.status() == OBDStatus.CAR_CONNECTED

    def test_cmd(self, cmd):
        """Return whether the command is supported. Always True when no PID cache is used."""
        return True

    async def query(self, cmd, force=False):
        """Primary API function. Send commands to the car, and protect against sending unsupported commands."""

        return await self.capture_command(cmd, force=force)

    async def capture_command(self, cmd, force=False):
        """Send a command and retain the raw adapter lines alongside the decoded response."""

        if self.status() == OBDStatus.NOT_CONNECTED:
            logger.warning("Query failed, no connection available")
            return OBDResponse()

        if cmd.kwp2000:
            return await self._query_kwp2000(cmd)

        if cmd.can_monitor:
            return await self._query_can_broadcast(cmd)

        # if the user forces, skip all checks
        if not force and not self.test_cmd(cmd):
            return OBDResponse()

        await self.__set_header(cmd.header)

        logger.info("Sending command: %s", cmd)
        cmd_string = self.__build_command_string(cmd)
        raw_lines = await self.interface.send_raw(cmd_string)
        messages = self.interface.parse_lines(raw_lines)

        response = OBDResponse(cmd, messages)
        response.raw_lines = raw_lines or []

        if not messages:
            logger.info("No valid OBD Messages returned")
            return response

        for f in messages[0].frames:
            logger.debug("Received frame: %s", f.raw)

        # if we don't already know how many frames this command returns,
        # log it, so we can specify it next time
        if cmd not in self.__frame_counts:
            self.__frame_counts[cmd] = sum([len(m.frames) for m in messages])

        for m in messages:
            if len(m.data) == 0 and (m.raw() == "NO DATA" or m.raw() == "CAN ERROR"):
                logger.info("Vehicle not responding")
                return response

        decoded_response = cmd(messages)  # applies command-specific message sizing before decode
        decoded_response.raw_lines = response.raw_lines
        return decoded_response

    async def _query_kwp2000(self, cmd):
        """Execute a KWP2000 multi-step diagnostic sequence.
        
        For odometer: sends session start (0x0210C0) then data read (0x022101).
        Requires explicit sequencing with responses between steps.
        """
        
        # Set header to target ECU (0x743 for CAR-CAN odometer)
        await self.__set_header(cmd.header)
        
        raw_lines_all = []
        
        # Step 1: Send session start (0x0210C0)
        logger.info("KWP2000: Sending diagnostic session start (0x0210C0)")
        raw_lines_session = await self.interface.send_raw(b"0210C0")
        raw_lines_all.extend(raw_lines_session or [])
        messages_session = self.interface.parse_lines(raw_lines_session)
        
        if not messages_session or not messages_session[0].data:
            logger.warning("KWP2000: No response to session start - continuing anyway")
        else:
            logger.info(f"KWP2000: Session response ({len(messages_session)} msgs, {len(messages_session[0].data)} bytes): {messages_session[0].data.hex()}")
        
        # Small delay to ensure session is established
        await asyncio.sleep(0.05)
        
        # Step 2: Send data read request (0x022101) 
        logger.info("KWP2000: Sending data read request (0x022101)")
        raw_lines_data = await self.interface.send_raw(cmd.command)
        raw_lines_all.extend(raw_lines_data or [])
        messages_data = self.interface.parse_lines(raw_lines_data)
        
        response = OBDResponse(cmd, messages_data)
        response.raw_lines = raw_lines_all
        
        if not messages_data:
            logger.info("KWP2000: No response to data read request")
            return response

        for m in messages_data:
            if len(m.data) == 0 and (m.raw() == "NO DATA" or m.raw() == "CAN ERROR"):
                logger.info("KWP2000: Vehicle not responding")
                return response
        
        logger.info(f"KWP2000: Data response ({len(messages_data)} msgs):")
        for i, msg in enumerate(messages_data):
            logger.info(f"  Message {i}: {len(msg.data)} bytes: {msg.data.hex()}")
        
        for f in messages_data[0].frames:
            logger.debug("KWP2000: Received frame: %s", f.raw)
        
        # Decode the response
        decoded_response = cmd(messages_data)
        decoded_response.raw_lines = response.raw_lines
        return decoded_response

    async def _query_can_broadcast(self, cmd):
        """Read a passive CAN broadcast frame and decode it using the command decoder."""
        if self.status() != OBDStatus.CAR_CONNECTED:
            return OBDResponse()

        if self.interface is None:
            return OBDResponse()

        can_id_str = cmd.command.decode().strip().upper()
        lines = await self.interface.read_can_broadcast(can_id_str)
        if not lines:
            response = OBDResponse(cmd)
            response.raw_lines = []
            return response

        # In monitor mode (ATH1 is active), ELM outputs lines formatted as:
        # "<CAN_ID><DATA_BYTES>" or space-separated "<CAN_ID> <D0> <D1> ...".
        # Passive CAN broadcasts are raw frames, NOT ISO-TP diagnostic frames.
        # Routing them through CANProtocol fails because byte 0 is not an ISO-TP PCI byte.
        parsed_messages = []
        for line in lines:
            cleaned = line.replace(" ", "").strip()
            if not isHex(cleaned):
                continue

            # Check if this frame matches the requested CAN ID
            if cleaned.upper().startswith(can_id_str):
                payload_hex = cleaned[len(can_id_str):]
            elif len(cleaned) == 16:
                # 8 data bytes without header echo
                payload_hex = cleaned
            else:
                continue

            try:
                data_bytes = bytearray.fromhex(payload_hex)
            except ValueError:
                continue

            if len(data_bytes) == 8:
                frame = Frame(line)
                frame.data = data_bytes
                msg = Message([frame])
                msg.data = data_bytes
                parsed_messages.append(msg)

        if not parsed_messages:
            response = OBDResponse(cmd)
            response.raw_lines = lines
            return response

        response = cmd(parsed_messages)
        response.raw_lines = lines
        return response

    def __build_command_string(self, cmd):
        """Assemble the appropriate command string."""
        cmd_string = cmd.command

        # if we know the number of frames that this command returns,
        # only wait for exactly that number. This avoids some harsh
        # timeouts from the ELM, thus speeding up queries.
        if self.fast and cmd.fast and (cmd in self.__frame_counts):
            cmd_string += str(self.__frame_counts[cmd]).encode()

        return cmd_string

