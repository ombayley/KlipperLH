"""Tests for deck coordinate resolution."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from examples.dep.lh.deck import Deck
from examples.dep.lh import MotionError


@pytest.mark.asyncio
async def test_slot_resolution_uses_standard_96_well_layout() -> None:
    """Deck resolution should map standard wells to absolute coordinates."""

    deck_file = Path("tests") / f"deck-{uuid4().hex}.yaml"
    try:
        deck_file.write_text(
            "\n".join(
                [
                    "deck:",
                    "  labware:",
                    "    plate_96:",
                    "      rows: 8",
                    "      columns: 12",
                    "      pitch_x_mm: 9.0",
                    "      pitch_y_mm: 9.0",
                    "      offset_x_mm: 0.0",
                    "      offset_y_mm: 0.0",
                    "      z_mm: 1.5",
                    "  slots:",
                    "    A1:",
                    "      name: Sample Plate",
                    "      origin_x: 10.0",
                    "      origin_y: 20.0",
                    "      origin_z: 2.0",
                    "      labware_type: plate_96",
                ]
            ),
            encoding="utf-8",
        )

        deck = Deck.from_yaml(deck_file)

        assert deck.resolve("A1", "B2") == pytest.approx((19.0, 29.0, 3.5))
    finally:
        deck_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_unknown_slot_raises_motion_error() -> None:
    """Resolving an unknown slot should raise a motion error."""

    deck_file = Path("tests") / f"deck-{uuid4().hex}.yaml"
    try:
        deck_file.write_text(
            "\n".join(
                [
                    "deck:",
                    "  slots:",
                    "    A1:",
                    "      name: Sample Plate",
                    "      origin_x: 0.0",
                    "      origin_y: 0.0",
                ]
            ),
            encoding="utf-8",
        )

        deck = Deck.from_yaml(deck_file)

        with pytest.raises(MotionError):
            deck.resolve("B1", "A1")
    finally:
        deck_file.unlink(missing_ok=True)
