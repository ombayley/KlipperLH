"""Async Moonraker JSON-RPC client with reconnect support."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from .config import MoonrakerConfig
from .exceptions import MoonrakerError
from .protocols import JSONValue, NotificationHandler, NotificationMessage

LOGGER = logging.getLogger(__name__)


class MoonrakerClient:
    """JSON-RPC client for Moonraker's WebSocket API."""

    def __init__(self, config: MoonrakerConfig) -> None:
        """Initialise the client with connection settings."""

        self._config = config
        self._uri = f"ws://{config.host}:{config.port}/websocket"
        self._request_id = 0
        self._pending: dict[int, asyncio.Future[JSONValue]] = {}
        self._notification_listeners: dict[str, list[NotificationHandler]] = defaultdict(list)
        self._object_subscriptions: dict[str, list[str] | None] = {}
        self._notification_tasks: set[asyncio.Task[None]] = set()
        self._ready_event = asyncio.Event()
        self._connected_event = asyncio.Event()
        self._connect_lock = asyncio.Lock()
        self._closing = False
        self._listener_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._websocket: Any | None = None

    async def connect(self) -> None:
        """Connect to Moonraker and start the listener loop."""

        async with self._connect_lock:
            self._closing = False
            if self._connected_event.is_set() and self._websocket is not None:
                return
            await self._open_connection()

    async def disconnect(self) -> None:
        """Disconnect from Moonraker and stop reconnect attempts."""

        self._closing = True
        self._ready_event.clear()
        self._connected_event.clear()

        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            await self._await_cancel(self._reconnect_task)
            self._reconnect_task = None

        if self._listener_task is not None:
            self._listener_task.cancel()
            await self._await_cancel(self._listener_task)
            self._listener_task = None

        for task in list(self._notification_tasks):
            task.cancel()
            await self._await_cancel(task)

        if self._websocket is not None:
            await self._websocket.close()
            self._websocket = None

        self._reject_pending(MoonrakerError("Moonraker client disconnected"))

    async def rpc(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None = None,
    ) -> JSONValue:
        """Send a JSON-RPC request and await its result."""

        websocket = await self._wait_for_connection()
        request_id = self._next_request_id()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[JSONValue] = loop.create_future()
        self._pending[request_id] = future

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": dict(params or {}),
            "id": request_id,
        }

        try:
            await websocket.send(json.dumps(payload))
        except Exception as exc:
            self._pending.pop(request_id, None)
            raise MoonrakerError(f"failed to send RPC '{method}'") from exc

        return await future

    def send_fire_forget(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None = None,
    ) -> asyncio.Task[None]:
        """Send a request without awaiting the response future."""

        return asyncio.create_task(self._send_without_waiting(method, params))

    async def wait_ready(self) -> None:
        """Wait until Moonraker reports the `ready` Klippy state."""

        if not self._connected_event.is_set():
            await self.connect()

        if self._ready_event.is_set():
            return

        while not self._ready_event.is_set():
            try:
                response = await self.rpc("server.info")
            except MoonrakerError:
                await self._connected_event.wait()
                await asyncio.sleep(0.1)
                continue

            state = self._extract_klippy_state(response)
            if state == "ready":
                self._ready_event.set()
                return

            await asyncio.sleep(0.1)

    async def subscribe_objects(
        self,
        objects: Mapping[str, Sequence[str] | None],
    ) -> JSONValue:
        """Subscribe to Moonraker object updates and remember the subscription."""

        merged = self._merge_object_subscriptions(objects)
        return await self.rpc("printer.objects.subscribe", self._subscription_payload(merged))

    def add_notification_listener(
        self,
        method: str,
        listener: NotificationHandler,
    ) -> None:
        """Register a callback for a Moonraker notification method."""

        listeners = self._notification_listeners[method]
        if listener not in listeners:
            listeners.append(listener)

    def remove_notification_listener(
        self,
        method: str,
        listener: NotificationHandler,
    ) -> None:
        """Remove a previously registered notification callback."""

        listeners = self._notification_listeners.get(method)
        if listeners is None:
            return
        self._notification_listeners[method] = [
            existing for existing in listeners if existing is not listener
        ]

    async def _open_connection(self) -> None:
        """Open a websocket connection and perform post-connect setup."""

        try:
            self._websocket = await websockets.connect(
                self._uri,
                open_timeout=self._config.connect_timeout_s,
                close_timeout=self._config.connect_timeout_s,
            )
        except Exception as exc:
            raise MoonrakerError(f"failed to connect to Moonraker at {self._uri}") from exc

        self._connected_event.set()
        self._listener_task = asyncio.create_task(self._listener_loop())

        await self.rpc(
            "server.connection.identify",
            {
                "client_name": "KlipperLH",
                "version": "0.1.0",
                "type": "agent",
                "url": "https://github.com/ombayley/KlipperLH",
            },
        )
        await self._resubscribe()
        await self._refresh_ready_state()

    async def _listener_loop(self) -> None:
        """Receive websocket messages and dispatch responses or notifications."""

        websocket = self._websocket
        if websocket is None:
            return

        try:
            async for raw_message in websocket:
                await self._handle_message(raw_message)
        except asyncio.CancelledError:
            raise
        except ConnectionClosed:
            if not self._closing:
                self._handle_disconnect()
        except Exception:
            if not self._closing:
                LOGGER.exception("Moonraker listener failed")
                self._handle_disconnect()

    async def _handle_message(self, raw_message: str) -> None:
        """Decode and route a websocket message."""

        decoded = json.loads(raw_message)
        if not isinstance(decoded, dict):
            LOGGER.debug("ignoring non-object Moonraker message: %r", decoded)
            return

        message = decoded
        if "id" in message:
            await self._handle_response(message)
            return

        method = message.get("method")
        if not isinstance(method, str):
            return

        if method == "notify_klippy_ready":
            self._ready_event.set()
        elif method in {"notify_klippy_disconnected", "notify_klippy_shutdown"}:
            self._ready_event.clear()

        self._dispatch_notification(method, message)

    async def _handle_response(self, message: dict[str, Any]) -> None:
        """Resolve a pending JSON-RPC request."""

        request_id = message.get("id")
        if not isinstance(request_id, int):
            return

        future = self._pending.pop(request_id, None)
        if future is None or future.done():
            return

        if "error" in message:
            error = message["error"]
            future.set_exception(self._format_rpc_error(error))
            return

        future.set_result(message.get("result"))

    def _dispatch_notification(
        self,
        method: str,
        message: NotificationMessage,
    ) -> None:
        """Send a notification payload to registered listeners."""

        for listener in list(self._notification_listeners.get(method, [])):
            task = asyncio.create_task(self._run_listener(listener, message))
            self._notification_tasks.add(task)
            task.add_done_callback(self._notification_tasks.discard)

    async def _run_listener(
        self,
        listener: NotificationHandler,
        message: NotificationMessage,
    ) -> None:
        """Run a single notification listener."""

        result = listener(message)
        if inspect.isawaitable(result):
            await result

    async def _refresh_ready_state(self) -> None:
        """Synchronise the ready event with Moonraker's current state."""

        response = await self.rpc("server.info")
        state = self._extract_klippy_state(response)
        if state == "ready":
            self._ready_event.set()
        else:
            self._ready_event.clear()

    def _extract_klippy_state(self, response: JSONValue) -> str | None:
        """Extract Klippy state from a `server.info` response."""

        if not isinstance(response, dict):
            return None
        state = response.get("klippy_state")
        if isinstance(state, str):
            return state
        return None

    def _handle_disconnect(self) -> None:
        """Update connection state and start the reconnect loop."""

        self._connected_event.clear()
        self._ready_event.clear()
        self._websocket = None
        self._reject_pending(MoonrakerError("Moonraker connection lost"))
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnect with exponential backoff and replay subscriptions."""

        attempt = 0
        while not self._closing:
            if (
                self._config.reconnect_max_attempts is not None
                and attempt >= self._config.reconnect_max_attempts
            ):
                return

            delay_s = min(0.5 * (2**attempt), 30.0)
            await asyncio.sleep(delay_s)

            try:
                async with self._connect_lock:
                    if self._closing:
                        return
                    await self._open_connection()
            except MoonrakerError:
                attempt += 1
                continue

            return

    async def _send_without_waiting(
        self,
        method: str,
        params: Mapping[str, JSONValue] | None,
    ) -> None:
        """Send a request while deliberately not awaiting the response future."""

        websocket = await self._wait_for_connection()
        request_id = self._next_request_id()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[JSONValue] = loop.create_future()
        self._pending[request_id] = future
        future.add_done_callback(self._consume_fire_and_forget_result)

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": dict(params or {}),
            "id": request_id,
        }

        try:
            await websocket.send(json.dumps(payload))
        except Exception as exc:
            self._pending.pop(request_id, None)
            future.set_exception(MoonrakerError(f"failed to send RPC '{method}'"))
            LOGGER.warning("fire-and-forget send failed for %s: %s", method, exc)
            return

    def _consume_fire_and_forget_result(self, future: asyncio.Future[JSONValue]) -> None:
        """Consume fire-and-forget futures to avoid unhandled warnings."""

        try:
            future.result()
        except MoonrakerError as exc:
            LOGGER.warning("fire-and-forget RPC failed: %s", exc)
        except asyncio.CancelledError:
            return

    async def _wait_for_connection(self) -> Any:
        """Wait until a websocket transport is available."""

        if not self._connected_event.is_set():
            if self._closing:
                raise MoonrakerError("Moonraker client is closing")
            await self.connect()
            if not self._connected_event.is_set():
                await self._connected_event.wait()

        if self._websocket is None:
            raise MoonrakerError("Moonraker websocket is unavailable")

        return self._websocket

    def _merge_object_subscriptions(
        self,
        objects: Mapping[str, Sequence[str] | None],
    ) -> dict[str, list[str] | None]:
        """Merge a new object subscription into the replay cache."""

        for object_name, fields in objects.items():
            existing = self._object_subscriptions.get(object_name)
            if fields is None:
                self._object_subscriptions[object_name] = None
                continue
            merged_fields = set(existing or [])
            merged_fields.update(fields)
            self._object_subscriptions[object_name] = sorted(merged_fields)
        return dict(self._object_subscriptions)

    def _subscription_payload(
        self,
        objects: Mapping[str, Sequence[str] | None],
    ) -> dict[str, JSONValue]:
        """Convert stored object subscriptions into a JSON-serialisable payload."""

        object_payload: dict[str, JSONValue] = {}
        for object_name, fields in objects.items():
            if fields is None:
                object_payload[object_name] = None
                continue
            json_fields: list[JSONValue] = [field for field in fields]
            object_payload[object_name] = json_fields
        return {"objects": object_payload}

    async def _resubscribe(self) -> None:
        """Replay subscriptions after reconnecting."""

        if not self._object_subscriptions:
            return
        await self.rpc(
            "printer.objects.subscribe",
            self._subscription_payload(self._object_subscriptions),
        )

    def _reject_pending(self, exc: MoonrakerError) -> None:
        """Fail all in-flight requests with a connection error."""

        for future in self._pending.values():
            if not future.done():
                future.set_exception(exc)
        self._pending.clear()

    def _next_request_id(self) -> int:
        """Return the next monotonic JSON-RPC request id."""

        self._request_id += 1
        return self._request_id

    def _format_rpc_error(self, error: Any) -> MoonrakerError:
        """Normalise a Moonraker error payload into a domain exception."""

        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message", "unknown Moonraker error")
            details = error.get("data")
            return MoonrakerError(
                f"Moonraker RPC error code={code!r} message={message!r} data={details!r}"
            )
        return MoonrakerError(f"Moonraker RPC error: {error!r}")

    async def _await_cancel(self, task: asyncio.Task[None]) -> None:
        """Await a cancelled task without leaking cancellation noise."""

        try:
            await task
        except asyncio.CancelledError:
            return
