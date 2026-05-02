"""Small direct Moonraker websocket client.

The client deliberately keeps Moonraker's JSON-RPC shape visible:

    await client.open()
    await client.gcode("G28")
    info = await client.request("server.info")
    await client.close()

Use ``send`` and ``receive`` when you want to see the individual websocket
messages. Use ``request`` when you want the common send-and-wait-for-reply path.
"""

from __future__ import annotations
import asyncio
import json
import websockets
from typing import Callable
from klipper_lh.logging import get_logger
from klipper_lh.config import MoonrakerConfig

log = get_logger(name="MoonrakerClient")

class MoonrakerClient:
    def __init__(self, config: MoonrakerConfig):
        self.uri = f"ws://{config.host}:{config.port}/websocket"
        self.ws = None
        self.pending: dict[int, asyncio.Future] = {}
        self.next_id = 1
        self.device_state: dict = {}
        self._listener_task = None
        self._notification_handlers: dict[str, list[Callable]] = {}

    # ── Connection ────────────────────────────────────────────────────────────────────────────────────────────────────
    async def connect(self):
        self.ws = await websockets.connect(self.uri)
        self._listener_task = asyncio.create_task(self._listen())
        log.debug("Moonraker Client Connected")

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
        await self.ws.close()
        log.debug("Moonraker Client Connected")

    async def _listen(self):
        async for raw in self.ws:
            msg = json.loads(raw)

            # --- Handle Response ---
            if "id" in msg:
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(RuntimeError(msg["error"]["message"]))
                    else:
                        fut.set_result(msg["result"])

            # --- Handle Notification ---
            else:
                self._dispatch_notification(msg)

    # ── Requests ──────────────────────────────────────────────────────────────────────────────────────────────────────
    async def request(self, method: str, params: dict = None):
        msg_id = self.next_id
        self.next_id += 1
        fut = asyncio.get_event_loop().create_future()
        self.pending[msg_id] = fut

        req=json.dumps({
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params or {}
        })

        await self.ws.send(req)
        log.debug(f"Sent Request: {req}")
        resp = await fut
        log.debug(f"Received Response: {resp}")

        return resp

    # ── Notifications ─────────────────────────────────────────────────────────────────────────────────────────────────
    def on_notification(self, method: str, callback: Callable):
        """Register a callback for a specific Moonraker notification method."""
        self._notification_handlers.setdefault(method, []).append(callback)

    def _dispatch_notification(self, msg: dict):
        method = msg.get("method", "")
        params = msg.get("params", [])

        # Built-in handling for status updates (merge diffs into local state)
        if method == "notify_status_update":
            diff = params[0]
            log.debug(f"Notification: {diff}")
            for key, val in diff.items():
                self.device_state[key] = {**self.device_state.get(key, {}), **val}

        # Call any registered callbacks
        for cb in self._notification_handlers.get(method, []):
            try:
                cb(params)
            except Exception as e:
                print(f"Handler error for {method}: {e}")
