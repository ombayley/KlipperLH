"""Compatibility import for the old component websocket name."""

from .client import KlipperWebSocket, MoonrakerClient, MoonrakerError

__all__ = ["KlipperWebSocket", "MoonrakerClient", "MoonrakerError"]
