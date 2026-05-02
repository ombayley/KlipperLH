"""Liquid-level detection helpers."""

from __future__ import annotations

from .config import MotionConfig
from .deck import Deck
from .protocols import Mover, Prober
from .tools import ToolHead


class LevelDetector:
    """Move above a well and run a probing cycle."""

    def __init__(
        self,
        deck: Deck,
        mover: Mover,
        prober: Prober,
        motion_config: MotionConfig,
        tool: ToolHead | None = None,
    ) -> None:
        """Initialise a level detector from motion and deck primitives."""

        self._deck = deck
        self._mover = mover
        self._prober = prober
        self._motion_config = motion_config
        self._tool = tool

    async def detect(self, slot: str, well: str, *, approach_height_mm: float | None = None) -> float:
        """Move above a well and return the probed Z value."""

        x, y, z = self._deck.resolve(slot, well)
        if self._tool is not None:
            x, y, z = self._tool.apply_offsets(x, y, z)

        safe_height = max(
            z + (approach_height_mm or self._motion_config.safe_z_height_mm),
            self._motion_config.safe_z_height_mm,
        )
        await self._mover.move(
            X=x,
            Y=y,
            Z=safe_height,
            speed=self._motion_config.default_speed_mm_s,
            wait=True,
        )
        return await self._prober.probe_z()
