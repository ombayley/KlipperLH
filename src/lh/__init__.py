"""Klipper liquid-handling toolkit."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "Deck": ("deck", "Deck"),
    "LHConfig": ("config", "LHConfig"),
    "LevelDetector": ("level_detect", "LevelDetector"),
    "LiquidHandlerSession": ("session", "LiquidHandlerSession"),
    "MoonrakerClient": ("client", "MoonrakerClient"),
    "MotionController": ("motion", "MotionController"),
    "Pipette": ("pipette", "Pipette"),
    "ToolHead": ("tools", "ToolHead"),
    "load_config": ("config", "load_config"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Lazily import public objects so optional runtime deps stay optional at import time."""

    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    module = import_module(f".{module_name}", __name__)
    return getattr(module, attribute_name)
