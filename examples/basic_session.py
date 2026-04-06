"""Minimal example for opening a liquid-handler session."""

from __future__ import annotations

import asyncio
from pathlib import Path

from lh.client import MoonrakerClient
from lh.config import load_config
from lh.deck import Deck
from lh.level_detect import LevelDetector
from lh.motion import MotionController
from lh.pipette import Pipette
from lh.session import LiquidHandlerSession
from lh import ToolHead


async def main() -> None:
    """Load configuration, open a session, and run a simple aspirate cycle."""

    config = load_config(Path("src/device_config/default.yaml"))
    client = MoonrakerClient(config.moonraker)
    motion = MotionController(client=client, config=config.motion)
    deck = Deck(config.deck)
    tool = ToolHead(config.tool)
    pipette = Pipette(mover=motion, config=config.pipette)
    level_detector = LevelDetector(
        deck=deck,
        mover=motion,
        prober=motion,
        motion_config=config.motion,
        tool=tool,
    )

    async with LiquidHandlerSession(
        connection=client,
        mover=motion,
        motion_config=config.motion,
        tool=tool,
        prober=motion,
        deck=deck,
        pipette=pipette,
        level_detector=level_detector,
    ) as session:
        await session.move_to_well("A1", "A1")
        await pipette.aspirate(50.0)
        detected_z = await level_detector.detect("A1", "A1")
        print(f"Detected liquid at Z={detected_z:.3f} mm")


if __name__ == "__main__":
    asyncio.run(main())
