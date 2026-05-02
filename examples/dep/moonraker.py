#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: Moonraker JSON-RPC client.

Responsibilities:
  - Open / close the WebSocket connection
  - Send requests and correlate responses by id
  - Dispatch notifications to registered handlers
  - Reconnect automatically with exponential backoff
  - Enforce per-request timeouts
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Callable

from klipper_lh.logging import get_logger
from klipper_lh.config import MoonrakerConfig

log = get_logger(name="MoonrakerClient")


class MoonrakerClient:
    def __init__(self, config: MoonrakerConfig):
        self._uri = f"ws://{config.host}:{config.port}/websocket"
        self._request_timeout = float(config.request_timeout)
        self._reconnect_delay = float(config.reconnect_delay)
        self._max_reconnect_delay = float(config.max_reconnect_delay)

        self._ws = None
        self._listener_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id: int = 1

        # method → [handler, ...]
        # Callers register here; this client never looks at the method strings
        self._notification_handlers: dict[str, list[Callable[[list], None]]] = {}

        # Optional lifecycle hooks — useful for callers that need to
        # re-subscribe or re-sync state after a reconnect
        self._on_connected:    list[Callable] = []
        self._on_disconnected: list[Callable] = []

        self._intentional_close = False
        self._current_delay = self._reconnect_delay

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def on_connected(self, cb: Callable) -> MoonrakerClient:
        """Called each time the connection is (re)established."""
        self._on_connected.append(cb)
        return self

    def on_disconnected(self, cb: Callable) -> MoonrakerClient:
        """Called each time the connection drops unexpectedly."""
        self._on_disconnected.append(cb)
        return self

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """
        Connect and start the listener.
        Does not reconnect — call connect_with_retry() if you want that.
        """
        self._intentional_close = False
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError("Install the 'websockets' package to use MoonrakerClient") from exc

        self._ws = await websockets.connect(self._uri)
        self._listener_task = asyncio.create_task(self._listen())
        log.debug("Connected to Moonraker")
        await self._fire(self._on_connected)

    async def connect_with_retry(self):
        """
        Connect and keep reconnecting forever until disconnect() is called.
        Suitable for long-running processes (instrument control, etc.).
        """
        self._intentional_close = False
        self._current_delay = self._reconnect_delay
        attempt = 0

        while not self._intentional_close:
            try:
                await self.connect()
                self._current_delay = self._reconnect_delay  # reset on success
                attempt = 0

                # Block until the listener exits — re-raises if it crashed
                await self._listener_task

            except asyncio.CancelledError:
                # disconnect() cancelled the task intentionally — stop cleanly
                break

            except Exception as exc:
                if self._intentional_close:
                    break
                attempt += 1
                log.warning(f"Connection failed (attempt {attempt}): {exc}")
                await self._fire(self._on_disconnected)

            if self._intentional_close:
                break

            jitter = (random.random() - 0.5) * 0.4 * self._current_delay
            delay = min(self._current_delay + jitter, self._max_reconnect_delay)
            log.info(f"Reconnecting in {delay:.1f}s")
            await asyncio.sleep(delay)
            self._current_delay = min(self._current_delay * 2, self._max_reconnect_delay)

    async def disconnect(self):
        self._intentional_close = True
        if self._listener_task:
            self._listener_task.cancel()
        if self._ws:
            await self._ws.close()
        self._fail_all_pending(RuntimeError("Client disconnected"))
        log.debug("Disconnected from Moonraker")

    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    # ── Listener ──────────────────────────────────────────────────────────────

    async def _listen(self):
        from websockets.exceptions import ConnectionClosed

        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as e:
                    log.warning(f"Bad JSON from Moonraker: {e}")
                    continue

                log.debug(f"Received: {msg}")

                if "id" in msg:
                    self._handle_response(msg)
                else:
                    self._dispatch_notification(msg)

        except ConnectionClosed:
            if not self._intentional_close:
                log.warning("Moonraker connection closed unexpectedly")
                self._fail_all_pending(RuntimeError("Connection closed"))
                await self._fire(self._on_disconnected)

    # ── Request / response ────────────────────────────────────────────────────

    async def request(self, method: str, params: dict | None = None) -> Any:
        """
        Send a JSON-RPC request and await its result.

        Raises RuntimeError on:
          - not connected
          - Moonraker returns an error object
          - no response within request_timeout seconds
        """
        if self._ws is None:
            raise RuntimeError("Not connected to Moonraker")

        msg_id = self._next_id
        self._next_id += 1
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = fut

        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params or {},
        })

        await self._ws.send(payload)
        log.debug(f"Sent: {payload}")

        try:
            result = await asyncio.wait_for(
                asyncio.shield(fut),
                timeout=self._request_timeout,
            )
            log.debug(f"Response for '{method}': {result}")
            return result

        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise RuntimeError(
                f"Request '{method}' timed out after {self._request_timeout}s"
            )

    def _handle_response(self, msg: dict):
        fut = self._pending.pop(msg["id"], None)
        if not fut or fut.done():
            return
        if "error" in msg:
            err = msg["error"]
            fut.set_exception(RuntimeError(f"[{err['code']}] {err['message']}"))
        else:
            fut.set_result(msg["result"])

    # ── Notifications ─────────────────────────────────────────────────────────

    def on_notification(self, method: str, callback: Callable[[list], None]) -> MoonrakerClient:
        """
        Register a handler for a Moonraker notification method.

        The handler receives the raw params list.
        Interpretation of params is entirely the caller's responsibility.

        Example:
            client.on_notification("notify_status_update", my_handler)
        """
        self._notification_handlers.setdefault(method, []).append(callback)
        return self

    def _dispatch_notification(self, msg: dict):
        method = msg.get("method", "")
        params = msg.get("params", [])
        handlers = self._notification_handlers.get(method, [])

        if not handlers:
            log.debug(f"Unhandled notification: {method}")
            return

        for cb in handlers:
            try:
                result = cb(params)
                # Support both sync and async handlers transparently
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                log.error(f"Notification handler error [{method}]: {e}")

    # ── Internals ─────────────────────────────────────────────────────────────

    def _fail_all_pending(self, exc: Exception):
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(exc)
        self._pending.clear()

    @staticmethod
    async def _fire(callbacks: list[Callable]) -> None:
        for cb in callbacks:
            try:
                result = cb()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                log.error(f"Lifecycle callback error: {e}")
