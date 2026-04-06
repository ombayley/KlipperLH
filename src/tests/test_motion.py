"""Tests for motion planning and probing."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Mapping, Sequence

import pytest

from lh.config import MotionConfig
from lh.motion import MotionController
from lh.protocols import JSONValue, NotificationHandler, NotificationMessage


class FakeRPCClient:
    """Minimal Moonraker-like client used by motion tests."""

    def __init__(self) -> None:
        """Initialise call tracking and listener state."""

        self.calls: list[tuple[str, dict[str, JSONValue]]] = []
        self.listeners: dict[str, list[NotificationHandler]] = {}

    async def rpc(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None = None,
    ) -> JSONValue:
        """Record RPC calls and emit probe notifications when requested."""

        payload = dict(params or {})
        self.calls.append((method, payload))

        if method == "printer.gcode.script" and payload.get("script") == "PROBE":
            await self._emit(
                "notify_gcode_response",
                {
                    "method": "notify_gcode_response",
                    "params": ["// probe at 0.000,0.000 is z=12.340000"],
                },
            )
            return {"result": "ok"}

        if method == "printer.objects.query":
            return {"status": {"print_stats": {"state": "standby"}}}

        return {"result": "ok"}

    def send_fire_forget(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None = None,
    ) -> asyncio.Task[None]:
        """Return a completed task to satisfy the RPC protocol."""

        return asyncio.create_task(self._fire_and_forget(method, params))

    async def subscribe_objects(
        self,
        objects: Mapping[str, Sequence[str] | None],
    ) -> JSONValue:
        """Record object subscriptions."""

        self.calls.append(("printer.objects.subscribe", {"objects": dict(objects)}))
        return {"result": "ok"}

    def add_notification_listener(
        self,
        method: str,
        listener: NotificationHandler,
    ) -> None:
        """Register a notification callback."""

        self.listeners.setdefault(method, []).append(listener)

    def remove_notification_listener(
        self,
        method: str,
        listener: NotificationHandler,
    ) -> None:
        """Unregister a notification callback."""

        if method not in self.listeners:
            return
        self.listeners[method] = [candidate for candidate in self.listeners[method] if candidate is not listener]

    async def _emit(self, method: str, message: NotificationMessage) -> None:
        """Dispatch a notification to registered listeners."""

        for listener in list(self.listeners.get(method, [])):
            result = listener(message)
            if inspect.isawaitable(result):
                await result

    async def _fire_and_forget(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None,
    ) -> None:
        """Record fire-and-forget calls without returning a response."""

        self.calls.append((method, dict(params or {})))


@pytest.mark.asyncio
async def test_move_coalescing_sends_one_rpc_call() -> None:
    """Two rapid moves should coalesce into a single script call."""

    client = FakeRPCClient()
    motion = MotionController(client=client, config=MotionConfig(coalesce_window_ms=20))

    first = asyncio.create_task(motion.move(X=10.0, speed=50.0, wait=False))
    second = asyncio.create_task(motion.move(Y=20.0, speed=50.0, wait=False))
    await asyncio.gather(first, second)

    script_calls = [call for call in client.calls if call[0] == "printer.gcode.script"]
    assert len(script_calls) == 1
    script = script_calls[0][1]["script"]
    assert isinstance(script, str)
    assert "G0 X10.000 F3000.000" in script
    assert "G0 Y20.000 F3000.000" in script


@pytest.mark.asyncio
async def test_probe_z_parses_gcode_response() -> None:
    """Probe results should be parsed from `notify_gcode_response` lines."""

    client = FakeRPCClient()
    motion = MotionController(client=client, config=MotionConfig())

    result = await motion.probe_z(timeout_s=1.0)

    assert result == pytest.approx(12.34)
    assert client.listeners.get("notify_gcode_response", []) == []
