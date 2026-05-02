"""Toolhead helpers."""

from __future__ import annotations

from .config import ToolConfig


class ToolHead:
    """Toolhead geometry and parking helper."""

    def __init__(self, config: ToolConfig) -> None:
        """Initialise the toolhead from validated configuration."""

        self._config = config

    def apply_offsets(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Apply tool offsets to a deck coordinate."""

        return (
            x + self._config.x_offset_mm,
            y + self._config.y_offset_mm,
            z + self._config.z_offset_mm,
        )

    def park_position(self) -> tuple[float, float, float]:
        """Return the configured tool parking position."""

        return (
            self._config.park_x_mm,
            self._config.park_y_mm,
            self._config.park_z_mm,
        )
