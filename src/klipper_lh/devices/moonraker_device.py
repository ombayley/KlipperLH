#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: Core device class that provides connectivity to the Moonraker API.
"""
from typing import Any
from klipper_lh.logging import get_logger
from klipper_lh.moonraker import MoonrakerClient
from klipper_lh.exceptions import DeviceConnectionError

# ──── Constants ──────────────────────────────────────────────────────────────────────────────────────
QueryObjects = dict[str, Any]

# ──── Core Class ─────────────────────────────────────────────────────────────────────────────────────
class MoonrakerDevice:
    """Higher level class to control the syringe pump that operates through the moonraker client."""

    def __init__(self, client: MoonrakerClient, name: str = "Device") -> None:
        self.client = client
        self.log = get_logger(name=name)

    # ──── Connectivity ───────────────────────────────────────────────────────────────────────────────
    async def connect(self) -> None:
        """Connect the underlying Moonraker client and validate the connection."""
        await self.client.connect()
        if not self.client.is_connected:
            raise DeviceConnectionError(f"Failed to connect to {self.__class__.__name__}")
        self.log.debug(f"Successfully connected to {self.__class__.__name__}")

    async def disconnect(self) -> None:
        """Disconnect the underlying Moonraker client."""
        await self.client.disconnect()
        self.log.debug(f"Successfully disconnected to {self.__class__.__name__}")

    @property
    def is_connected(self) -> bool:
        """Return True if Moonraker is currently connected."""
        return self.client.is_connected


    # ──── Moonraker messaging ─────────────────────────────────────────────────────────────────────────
    async def send_command(self, command: str) -> Any:
        """Send one G-code command through Moonraker."""
        return await self.client.request(
            method="printer.gcode.script",
            params={"script": command},
        )

    async def send_query(self, query: QueryObjects | str) -> Any:
        """Query one or more Moonraker printer objects."""
        if isinstance(query, str):
            query = {query: None}

        return await self.client.request(
            method="printer.objects.query",
            params={"objects": query},
        )

    async def get_status(self) -> str:
        """Return Klipper's current printer state string."""
        response = await self.client.request(method="printer.info")
        status = response["state"]
        self.log.debug(f"Status: {status}")
        return status

    async def wait_until_queue_empty(self) -> None:
        """Block until Klipper has completed all queued moves."""
        await self.send_command("M400")
