#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: Async Moonraker JSON-RPC client.

The client owns a single Moonraker WebSocket connection. Outgoing JSON-RPC
requests are assigned monotonically increasing ids and stored as pending
``asyncio.Future`` instances until Moonraker returns the matching response.

Moonraker notifications do not have JSON-RPC ids, so they are dispatched to
callbacks registered with :meth:`MoonrakerClient.on_notification`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from klipper_lh.config import MoonrakerConfig
from klipper_lh.logging import get_logger

# ──── Constants ──────────────────────────────────────────────────────────────────────────────────────
JsonObject = dict[str, Any]
NotificationParams = list[Any]
NotificationCallback = Callable[[NotificationParams], Awaitable[None] | None]

# ──── Client Class ───────────────────────────────────────────────────────────────────────────────────
class MoonrakerClient:
    """Minimal reconnectable Moonraker WebSocket client.

    Parameters
    ----------
    config:
        Moonraker connection settings, including host, port, and per-request
        timeout.
    """

    def __init__(self, config: MoonrakerConfig, name: str = "MoonrakerClient") -> None:
        self.log = get_logger(name=name)
        self._uri = f"ws://{config.host}:{config.port}/websocket"
        self._request_timeout = float(config.request_timeout)

        self._ws: Any | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._pending_responses: dict[int, asyncio.Future[Any]] = {}
        self._next_id: int = 1

        self._notification_handlers: dict[str, list[NotificationCallback]] = {}

        self._intentional_close = False

    # ──── Connectivity ───────────────────────────────────────────────────────────────────────────────
    async def connect(self) -> None:
        """Open the Moonraker WebSocket and start the background listener."""
        self._intentional_close = False
        self._ws = await websockets.connect(self._uri)
        self._listener_task = asyncio.create_task(self._listen())
        self.log.debug("Connected to Moonraker")

    async def disconnect(self) -> None:
        """Close the WebSocket connection and stop accepting responses."""
        self._intentional_close = True

        if self._ws is not None:
            await self._ws.close()
            self._ws = None

        if self._listener_task is not None:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None

        self._fail_all_pending(RuntimeError("Disconnected from Moonraker"))
        self.log.debug("Disconnected from Moonraker")

    @property
    def is_connected(self) -> bool:
        """Return True if the client is currently connected to Moonraker."""
        return self._ws is not None and self._ws.state is websockets.State.OPEN


    # ──── Listener ───────────────────────────────────────────────────────────────────────────────
    async def _listen(self) -> None:
        """Receive WebSocket messages and route them by JSON-RPC shape."""
        if self._ws is None:
            return

        try:
            async for raw_message in self._ws:
                try:
                    decoded_message = json.loads(raw_message)
                    if not isinstance(decoded_message, dict):
                        self.log.warning(f"Unexpected Moonraker message shape: {decoded_message}")
                        continue

                    message: JsonObject = decoded_message
                    self.log.debug(f"Received: {message}")
                except json.JSONDecodeError as exc:
                    self.log.warning(f"Bad JSON received from Moonraker: {exc}")
                    continue

                if "id" in message:
                    self._handle_response(message)
                else:
                    self._handle_notification(message)

        except ConnectionClosed:
            if not self._intentional_close:
                self.log.warning("Moonraker connection closed unexpectedly")
                self._fail_all_pending(RuntimeError("Connection closed"))


    # ──── Handlers ───────────────────────────────────────────────────────────────────────────────────
    def _handle_notification(self, message: JsonObject) -> None:
        """Dispatch one Moonraker notification to registered callbacks."""
        method = message.get("method", "")
        params = message.get("params", [])
        handlers = self._notification_handlers.get(method, [])

        if not handlers:
            self.log.debug(f"Unhandled notification: {method}")
            return

        for callback in handlers:
            try:
                result = callback(params)
                # Notification handlers may be normal functions or coroutines.
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as exc:
                self.log.error(f"Notification handler error [{method}]: {exc}")

    def on_notification(
        self,
        method: str,
        callback: NotificationCallback,
    ) -> MoonrakerClient:
        """Register a callback for a Moonraker notification method.

        The callback receives Moonraker's raw ``params`` list. Interpretation of
        those parameters is intentionally left to the caller because each
        notification method has its own payload structure.
        """
        self._notification_handlers.setdefault(method, []).append(callback)
        return self

    def _handle_response(self, message: JsonObject) -> None:
        """Resolve or reject the pending future for a JSON-RPC response."""
        request_id = message.get("id")
        response_future = self._pending_responses.pop(request_id, None)

        if response_future is None:
            self.log.debug(f"Received response for unknown request id: {request_id}")
            return

        if response_future.done():
            return

        if "error" in message:
            error = message["error"]
            code = error.get("code", "unknown")
            message_text = error.get("message", "Unknown error")
            response_future.set_exception(RuntimeError(f"[{code}] {message_text}"))
            return

        response_future.set_result(message.get("result"))


    # ──── Requests ───────────────────────────────────────────────────────────────────────────────────
    async def request(self, method: str, params: JsonObject | None = None) -> Any:
        """Send one JSON-RPC request and return its matching result.

        Raises
        ------
        RuntimeError
            If the client is disconnected, Moonraker returns an error response,
            or the response does not arrive before ``request_timeout``.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to Moonraker")

        request_id = self._get_next_request_id()
        response_future = self._create_response_future(request_id)
        request_message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        payload = json.dumps(request_message)

        await self._ws.send(payload)
        self.log.debug(f"Sent: {payload}")

        try:
            return await asyncio.wait_for(response_future, timeout=self._request_timeout)
        except asyncio.TimeoutError as exc:
            await self._pending_responses.pop(request_id, None)
            raise RuntimeError(
                f"Request '{method}' timed out after {self._request_timeout}s"
            ) from exc


    # ──── Internals ──────────────────────────────────────────────────────────────────────────────────
    def _get_next_request_id(self) -> int:
        """Return the next JSON-RPC id and advance the counter."""
        request_id = self._next_id
        self._next_id += 1
        return request_id

    def _create_response_future(self, request_id: int) -> asyncio.Future[Any]:
        """Create and store the future that will receive a response result."""
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending_responses[request_id] = future
        return future

    def _fail_all_pending(self, exc: Exception) -> None:
        """Reject every request still waiting for a Moonraker response."""
        for response_future in self._pending_responses.values():
            if not response_future.done():
                response_future.set_exception(exc)
        self._pending_responses.clear()
