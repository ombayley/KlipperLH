#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""
from dataclasses import dataclass

from .client import MoonrakerClient


@dataclass
class SyringePump:
    client: MoonrakerClient
    axis: str = "E"
    steps_per_ul: float = 2.4

    async def pump(self, volume_ul: float, flow_rate_mlmin: float) -> None:
        mm = volume_ul / self.steps_per_ul
        await self.client.gcode(f"G0 {self.axis}{mm:.4f}")
