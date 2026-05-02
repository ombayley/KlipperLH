#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""
from dataclasses import dataclass

from .client import MoonrakerClient


@dataclass
class KlipperGantry:
    client: MoonrakerClient

    async def move_to(self, x: float, y: float, z: float, speed: float = 100.0) -> None:
        await self.client.gcode(f"G0 X{x} Y{y} Z{z} F{speed * 60:.0f}")

    async def home(self) -> None:
        await self.client.gcode("G28")
