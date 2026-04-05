#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""
import asyncio
from dataclasses import dataclass, field
from socket import KlipperWebSocket


@dataclass
class KlipperGantry:
    ws: KlipperWebSocket

    async def move_to(self, x: float, y: float, z: float, speed: float = 100.0) -> None:
        await self.ws.send_gcode(f"G0 X{x} Y{y} Z{z} F{speed * 60:.0f}")

    async def home(self) -> None:
        await self.ws.send_gcode("G28")
