"""Configuration models and loader helpers."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .exceptions import ConfigurationError


class MoonrakerConfig(BaseModel):
    """Connection settings for Moonraker."""

    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"
    port: int = Field(default=7125, ge=1, le=65535)
    connect_timeout_s: float = Field(default=10.0, gt=0)
    reconnect_max_attempts: int | None = Field(default=None, ge=1)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "MoonrakerConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        if "moonraker" in data.keys():
            data = data["moonraker"]
        return cls(**data)


class MotionConfig(BaseModel):
    """Motion defaults for the liquid handler."""

    model_config = ConfigDict(extra="forbid")

    default_speed_mm_s: float = Field(default=100.0, gt=0)
    coalesce_window_ms: int = Field(default=5, ge=0)
    home_on_connect: bool = True
    safe_z_height_mm: float = Field(default=20.0, ge=0)


class LabwareLayoutConfig(BaseModel):
    """Well layout metadata for a labware type."""

    model_config = ConfigDict(extra="forbid")

    rows: int = Field(default=8, ge=1)
    columns: int = Field(default=12, ge=1)
    pitch_x_mm: float = Field(default=9.0, gt=0)
    pitch_y_mm: float = Field(default=9.0, gt=0)
    offset_x_mm: float = 0.0
    offset_y_mm: float = 0.0
    z_mm: float = 0.0


class DeckSlotConfig(BaseModel):
    """Physical slot definition on the deck."""

    model_config = ConfigDict(extra="forbid")

    name: str
    origin_x: float
    origin_y: float
    origin_z: float = 0.0
    labware_type: str | None = None
    layout: LabwareLayoutConfig | None = None


class DeckConfig(BaseModel):
    """Deck layout definition loaded from YAML."""

    model_config = ConfigDict(extra="forbid")

    slots: dict[str, DeckSlotConfig] = Field(default_factory=dict)
    labware: dict[str, LabwareLayoutConfig] = Field(
        default_factory=lambda: {"plate_96": LabwareLayoutConfig()}
    )


class ToolConfig(BaseModel):
    """Toolhead geometry and parking coordinates."""

    model_config = ConfigDict(extra="forbid")

    park_x_mm: float = 0.0
    park_y_mm: float = 0.0
    park_z_mm: float = 30.0
    x_offset_mm: float = 0.0
    y_offset_mm: float = 0.0
    z_offset_mm: float = 0.0


class PipetteConfig(BaseModel):
    """Pipette motion and calibration settings."""

    model_config = ConfigDict(extra="forbid")

    axis: str = "A"
    steps_per_ul: float = Field(gt=0)
    max_volume_ul: float = Field(gt=0)
    aspirate_speed_mm_s: float = Field(gt=0)
    dispense_speed_mm_s: float = Field(gt=0)

    @field_validator("axis")
    @classmethod
    def validate_axis(cls, value: str) -> str:
        """Normalise and validate the configured pipette axis."""

        axis = value.strip().upper()
        if not axis:
            raise ValueError("pipette axis must not be empty")
        return axis


class LHConfig(BaseModel):
    """Top-level configuration for the liquid handler."""

    model_config = ConfigDict(extra="forbid")

    moonraker: MoonrakerConfig = Field(default_factory=MoonrakerConfig)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    deck: DeckConfig = Field(default_factory=DeckConfig)
    tool: ToolConfig = Field(default_factory=ToolConfig)
    pipette: PipetteConfig


def load_config(path: Path) -> LHConfig:
    """Load and validate a liquid-handler configuration file."""

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"unable to read config file: {path}") from exc

    try:
        raw_data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in config file: {path}") from exc

    if raw_data is None:
        raw_data = {}

    if not isinstance(raw_data, dict):
        raise ConfigurationError("configuration root must be a mapping")

    try:
        return LHConfig.model_validate(raw_data)
    except ValidationError as exc:
        raise ConfigurationError("configuration validation failed") from exc
