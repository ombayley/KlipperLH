#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""

import asyncio
from klipper_lh.config import MoonrakerConfig
from klipper_lh.moonraker import MoonrakerClient
from klipper_lh.devices.gantry import Gantry
from klipper_lh.logging import get_logger

log = get_logger("Gantry_Tester")


async def main():
    cfg_p = r"C:\Users\OllyBayley\Documents\Repos\personal\KlipperLH\config\moonraker_wifi.yaml"
    mr_config = MoonrakerConfig.from_yaml(cfg_p)
    ws = MoonrakerClient(config=mr_config)
    gantry = Gantry(client=ws)

    await gantry.connect()
    log.info("Connected to Moonraker")

    await gantry.home(debug=True)
    log.info(f"Position after home bypass: {await gantry.get_current_position()}")

    await gantry.move(x=150, y=200, speed=200, power=0.5)
    log.info(f"Position after XY move: {await gantry.get_current_position()}")

    await gantry.disconnect()
    log.info("Disconnected from Moonraker")

if __name__ == "__main__":
    asyncio.run(main())
