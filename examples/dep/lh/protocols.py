"""Protocols shared across the liquid-handler package."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Protocol, TypeAlias, runtime_checkable

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
NotificationMessage: TypeAlias = dict[str, JSONValue]
NotificationHandler: TypeAlias = Callable[[NotificationMessage], Awaitable[None] | None]


@runtime_checkable
class SupportsConnection(Protocol):
    """Protocol for connection lifecycle management."""

    async def connect(self) -> None:
        """Open a connection to Moonraker."""

        ...

    async def disconnect(self) -> None:
        """Close the active Moonraker connection."""

        ...

    async def wait_ready(self) -> None:
        """Block until Moonraker reports that Klippy is ready."""

        ...


@runtime_checkable
class RPCClient(Protocol):
    """Protocol for JSON-RPC transport operations."""

    async def rpc(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None = None,
    ) -> JSONValue:
        """Send a JSON-RPC request and return the decoded result."""

        ...

    def send_fire_forget(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None = None,
    ) -> asyncio.Task[None]:
        """Send a JSON-RPC request without awaiting its response."""

        ...

    async def subscribe_objects(
        self,
        objects: Mapping[str, Sequence[str] | None],
    ) -> JSONValue:
        """Subscribe to Moonraker object status updates."""

        ...

    def add_notification_listener(
        self,
        method: str,
        listener: NotificationHandler,
    ) -> None:
        """Register a callback for a Moonraker notification method."""

        ...

    def remove_notification_listener(
        self,
        method: str,
        listener: NotificationHandler,
    ) -> None:
        """Unregister a callback for a Moonraker notification method."""

        ...


@runtime_checkable
class Mover(Protocol):
    """Protocol for motion primitives."""

    async def home(self, axes: str = "XYZ") -> None:
        """Home one or more axes."""

        ...

    async def move(
        self,
        *,
        speed: float | None = None,
        wait: bool = True,
        **axes: float,
    ) -> None:
        """Execute a move using named axis targets."""

        ...

    async def wait_for_idle(
        self,
        timeout_s: float = 10.0,
        poll_interval_s: float = 0.05,
    ) -> None:
        """Block until Klipper reports an idle toolhead."""

        ...


@runtime_checkable
class Prober(Protocol):
    """Protocol for probing primitives."""

    async def probe_z(self, *, timeout_s: float = 10.0) -> float:
        """Run a Z probe routine and return the reported height."""

        ...
