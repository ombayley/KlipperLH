"""Deck and labware coordinate resolution."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .config import DeckConfig, DeckSlotConfig, LabwareLayoutConfig
from .exceptions import ConfigurationError, MotionError


class Deck:
    """Resolve deck slots and well names into absolute XYZ coordinates."""

    def __init__(self, config: DeckConfig) -> None:
        """Create a deck resolver from validated configuration."""

        self._config = config

    @classmethod
    def from_yaml(cls, path: Path) -> "Deck":
        """Load a deck from YAML or from the `deck` section of a full config."""

        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(f"unable to read deck file: {path}") from exc

        try:
            raw_data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"invalid YAML in deck file: {path}") from exc

        if not isinstance(raw_data, dict):
            raise ConfigurationError("deck YAML must be a mapping")

        deck_data = raw_data.get("deck", raw_data)
        if not isinstance(deck_data, dict):
            raise ConfigurationError("deck configuration must be a mapping")

        try:
            config = DeckConfig.model_validate(deck_data)
        except ValidationError as exc:
            raise ConfigurationError("deck validation failed") from exc

        return cls(config)

    def resolve(self, slot: str, well: str) -> tuple[float, float, float]:
        """Resolve a slot and well name into absolute XYZ coordinates."""

        slot_config = self._resolve_slot(slot)
        layout = self._resolve_layout(slot_config)
        row_index, column_index = self._parse_well(well)

        if row_index >= layout.rows or column_index >= layout.columns:
            raise MotionError(
                f"well {well!r} is outside layout bounds {layout.rows}x{layout.columns}"
            )

        x = slot_config.origin_x + layout.offset_x_mm + (column_index * layout.pitch_x_mm)
        y = slot_config.origin_y + layout.offset_y_mm + (row_index * layout.pitch_y_mm)
        z = slot_config.origin_z + layout.z_mm
        return (x, y, z)

    def _resolve_slot(self, slot: str) -> DeckSlotConfig:
        """Find a slot by key or by configured display name."""

        direct_match = self._config.slots.get(slot)
        if direct_match is not None:
            return direct_match

        for key, candidate in self._config.slots.items():
            if candidate.name == slot or key.upper() == slot.upper():
                return candidate

        raise MotionError(f"unknown deck slot: {slot}")

    def _resolve_layout(self, slot_config: DeckSlotConfig) -> LabwareLayoutConfig:
        """Resolve the labware layout for a slot."""

        if slot_config.layout is not None:
            return slot_config.layout

        if slot_config.labware_type is None:
            return LabwareLayoutConfig()

        layout = self._config.labware.get(slot_config.labware_type)
        if layout is None:
            raise MotionError(f"unknown labware type: {slot_config.labware_type}")
        return layout

    def _parse_well(self, well: str) -> tuple[int, int]:
        """Parse a well name like `A1` into zero-based row and column indexes."""

        cleaned = well.strip().upper()
        if not cleaned:
            raise MotionError("well name must not be empty")

        row_part = ""
        column_part = ""
        for char in cleaned:
            if char.isalpha() and not column_part:
                row_part += char
            elif char.isdigit():
                column_part += char
            else:
                raise MotionError(f"invalid well identifier: {well}")

        if not row_part or not column_part:
            raise MotionError(f"invalid well identifier: {well}")

        row_index = self._row_label_to_index(row_part)
        column_index = int(column_part) - 1
        if column_index < 0:
            raise MotionError(f"invalid well identifier: {well}")
        return (row_index, column_index)

    def _row_label_to_index(self, row_label: str) -> int:
        """Convert an alphabetic row label into a zero-based index."""

        value = 0
        for char in row_label:
            value = (value * 26) + (ord(char) - ord("A") + 1)
        return value - 1
