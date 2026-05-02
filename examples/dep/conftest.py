"""Shared test fixtures."""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register the local asyncio marker for environments without pytest-asyncio."""

    config.addinivalue_line("markers", "asyncio: run the marked test in an asyncio event loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Run `async def` tests marked with `asyncio` in a fresh event loop."""

    if "asyncio" not in pyfuncitem.keywords:
        return None

    test_function = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_function):
        return None

    arguments = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(test_function(**arguments))
    return True


@pytest.fixture
def mock_client() -> AsyncMock:
    """Return an async mock that satisfies the motion and session protocols."""

    client = AsyncMock(name="mock_client")
    events: list[str] = []
    setattr(client, "events", events)

    async def connect() -> None:
        """Record a connection attempt."""

        events.append("connect")

    async def disconnect() -> None:
        """Record a disconnect attempt."""

        events.append("disconnect")

    async def wait_ready() -> None:
        """Record a ready wait."""

        events.append("wait_ready")

    async def home(*args: object, **kwargs: object) -> None:
        """Record a home command."""

        axes = "XYZ"
        if args:
            axes = str(args[0])
        elif isinstance(kwargs.get("axes"), str):
            axes = str(kwargs["axes"])
        events.append(f"home:{axes}")

    async def move(*args: object, **kwargs: object) -> None:
        """Record a move command."""

        _ = args
        _ = kwargs
        events.append("move")

    async def wait_for_idle(*args: object, **kwargs: object) -> None:
        """Record an idle wait."""

        _ = args
        _ = kwargs
        events.append("wait_for_idle")

    async def probe_z(*args: object, **kwargs: object) -> float:
        """Record a probe and return a deterministic height."""

        _ = args
        _ = kwargs
        events.append("probe_z")
        return 12.345

    client.connect = AsyncMock(side_effect=connect)
    client.disconnect = AsyncMock(side_effect=disconnect)
    client.wait_ready = AsyncMock(side_effect=wait_ready)
    client.home = AsyncMock(side_effect=home)
    client.move = AsyncMock(side_effect=move)
    client.wait_for_idle = AsyncMock(side_effect=wait_for_idle)
    client.probe_z = AsyncMock(side_effect=probe_z)
    return client
