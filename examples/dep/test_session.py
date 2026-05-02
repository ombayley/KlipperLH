"""Tests for session lifecycle orchestration."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, call

import pytest

from examples.dep.lh.config import MotionConfig, ToolConfig
from examples.dep.lh import Mover, SupportsConnection
from examples.dep.lh import LiquidHandlerSession
from examples.dep.lh.tools import ToolHead


@pytest.mark.asyncio
async def test_session_context_manager_runs_connect_home_park_disconnect(
    mock_client: AsyncMock,
) -> None:
    """The session context manager should run the full lifecycle."""

    session = LiquidHandlerSession(
        connection=cast(SupportsConnection, mock_client),
        mover=cast(Mover, mock_client),
        motion_config=MotionConfig(
            default_speed_mm_s=100.0,
            coalesce_window_ms=5,
            home_on_connect=True,
            safe_z_height_mm=20.0,
        ),
        tool=ToolHead(
            ToolConfig(
                park_x_mm=5.0,
                park_y_mm=6.0,
                park_z_mm=10.0,
            )
        ),
    )

    async with session as active_session:
        assert active_session is session

    mock_client.connect.assert_awaited_once()
    mock_client.wait_ready.assert_awaited_once()
    mock_client.home.assert_awaited_once_with()
    mock_client.disconnect.assert_awaited_once()
    assert mock_client.move.await_args_list == [
        call(Z=20.0, speed=100.0, wait=True),
        call(X=5.0, Y=6.0, speed=100.0, wait=True),
        call(Z=10.0, speed=100.0, wait=True),
    ]
    assert getattr(mock_client, "events") == [
        "connect",
        "wait_ready",
        "home:XYZ",
        "move",
        "move",
        "move",
        "disconnect",
    ]
