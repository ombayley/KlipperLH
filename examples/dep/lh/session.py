"""Async session orchestration for liquid-handling runs."""

from __future__ import annotations

from types import TracebackType

from .config import MotionConfig
from .deck import Deck
from .exceptions import ConfigurationError
from .level_detect import LevelDetector
from .pipette import Pipette
from .protocols import Mover, Prober, SupportsConnection
from .tools import ToolHead


class LiquidHandlerSession:
    """Manage connect, home, park, and disconnect lifecycle steps."""

    def __init__(
        self,
        connection: SupportsConnection,
        mover: Mover,
        *,
        motion_config: MotionConfig,
        tool: ToolHead,
        prober: Prober | None = None,
        deck: Deck | None = None,
        pipette: Pipette | None = None,
        level_detector: LevelDetector | None = None,
    ) -> None:
        """Build a session from connection, motion, and optional helpers."""

        self.connection = connection
        self.mover = mover
        self.motion_config = motion_config
        self.tool = tool
        self.prober = prober
        self.deck = deck
        self.pipette = pipette
        self.level_detector = level_detector

    async def __aenter__(self) -> "LiquidHandlerSession":
        """Connect to Moonraker and optionally home the machine."""

        await self.connection.connect()
        await self.connection.wait_ready()
        if self.motion_config.home_on_connect:
            await self.mover.home()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Park the toolhead and disconnect from Moonraker."""

        try:
            await self.park()
        finally:
            await self.connection.disconnect()

    async def park(self) -> None:
        """Move to the configured park position using a safe Z-first path."""

        park_x, park_y, park_z = self.tool.park_position()
        safe_z = max(park_z, self.motion_config.safe_z_height_mm)

        await self.mover.move(
            Z=safe_z,
            speed=self.motion_config.default_speed_mm_s,
            wait=True,
        )
        await self.mover.move(
            X=park_x,
            Y=park_y,
            speed=self.motion_config.default_speed_mm_s,
            wait=True,
        )
        if park_z != safe_z:
            await self.mover.move(
                Z=park_z,
                speed=self.motion_config.default_speed_mm_s,
                wait=True,
            )

    async def move_to_well(self, slot: str, well: str) -> tuple[float, float, float]:
        """Move to a resolved well coordinate and return the target point."""

        if self.deck is None:
            raise ConfigurationError("a deck is required to resolve wells")

        x, y, z = self.deck.resolve(slot, well)
        x, y, z = self.tool.apply_offsets(x, y, z)
        safe_z = max(z, self.motion_config.safe_z_height_mm)

        await self.mover.move(
            Z=safe_z,
            speed=self.motion_config.default_speed_mm_s,
            wait=True,
        )
        await self.mover.move(
            X=x,
            Y=y,
            speed=self.motion_config.default_speed_mm_s,
            wait=True,
        )
        await self.mover.move(
            Z=z,
            speed=self.motion_config.default_speed_mm_s,
            wait=True,
        )
        return (x, y, z)
