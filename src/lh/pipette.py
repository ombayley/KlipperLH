"""Pipette volume primitives."""

from __future__ import annotations

from .config import PipetteConfig
from .exceptions import PipetteError
from .protocols import Mover


class Pipette:
    """Volume-aware pipette wrapper around the motion layer."""

    def __init__(self, mover: Mover, config: PipetteConfig) -> None:
        """Initialise the pipette with a mover and calibration data."""

        self._mover = mover
        self._config = config
        self._current_volume_ul = 0.0

    @property
    def current_volume_ul(self) -> float:
        """Return the tracked liquid volume currently in the pipette."""

        return self._current_volume_ul

    async def aspirate(self, volume_ul: float, *, wait: bool = True) -> None:
        """Aspirate liquid from the source into the pipette."""

        self._validate_volume(volume_ul)
        if self._current_volume_ul + volume_ul > self._config.max_volume_ul:
            raise PipetteError("aspirate volume exceeds configured pipette capacity")

        distance = -self.volume_to_distance_mm(volume_ul)
        await self._mover.move(
            speed=self._config.aspirate_speed_mm_s,
            wait=wait,
            **{self._config.axis: distance},
        )
        self._current_volume_ul += volume_ul

    async def dispense(self, volume_ul: float, *, wait: bool = True) -> None:
        """Dispense liquid from the pipette."""

        self._validate_volume(volume_ul)
        if volume_ul > self._current_volume_ul:
            raise PipetteError("cannot dispense more than the tracked pipette volume")

        distance = self.volume_to_distance_mm(volume_ul)
        await self._mover.move(
            speed=self._config.dispense_speed_mm_s,
            wait=wait,
            **{self._config.axis: distance},
        )
        self._current_volume_ul -= volume_ul

    async def blow_out(self, *, wait: bool = True) -> None:
        """Dispense the currently tracked liquid volume."""

        if self._current_volume_ul <= 0:
            return
        await self.dispense(self._current_volume_ul, wait=wait)

    def volume_to_distance_mm(self, volume_ul: float) -> float:
        """Convert volume in microlitres into configured axis travel."""

        self._validate_volume(volume_ul)
        return volume_ul * self._config.steps_per_ul

    def _validate_volume(self, volume_ul: float) -> None:
        """Validate a positive, non-zero volume request."""

        if volume_ul <= 0:
            raise PipetteError("volume must be greater than zero")
