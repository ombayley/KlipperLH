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
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

JSON = str | int | float | bool | None | list["JSON"] | dict[str, "JSON"]


class MoonrakerError(Exception):
    """Raised when a Moonraker websocket or request operation fails."""


@dataclass
class MoonrakerClient:
    """Minimal async websocket client for Moonraker's JSON-RPC API."""

    host: str | Any = "127.0.0.1"
    port: int = 7125
    path: str = "/websocket"
    timeout_s: float = 10.0
    client_name: str = "KlipperLH"

    _ws: Any = field(default=None, init=False, repr=False)
    _next_id: int = field(default=0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _inbox: dict[int, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _messages: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Accept either simple host/port args or the existing config object."""

        if isinstance(self.host, str):
            return

        config = self.host
        self.host = getattr(config, "host", "127.0.0.1")
        self.port = int(getattr(config, "port", self.port))
        self.timeout_s = float(getattr(config, "connect_timeout_s", self.timeout_s))

    @property
    def uri(self) -> str:
        """Return the websocket URL used for Moonraker."""

        host = str(self.host)
        if host.startswith("ws://") or host.startswith("wss://"):
            return host if host.endswith(self.path) else f"{host}{self.path}"
        if ":" in host and not host.startswith("[") and host.count(":") > 1:
            host = f"[{host}]"
        return f"ws://{host}:{self.port}{self.path}"

    @property
    def is_open(self) -> bool:
        """Return true when a websocket object is available."""

        return self._ws is not None

    async def open(self, *, identify: bool = True) -> None:
        """Open the websocket connection."""

        if self._ws is not None:
            return

        try:
            import websockets

            self._ws = await websockets.connect(
                self.uri,
                open_timeout=self.timeout_s,
                close_timeout=self.timeout_s,
            )
        except ImportError as exc:
            raise MoonrakerError("install the 'websockets' package to use MoonrakerClient") from exc
        except Exception as exc:
            raise MoonrakerError(f"failed to open Moonraker websocket at {self.uri}") from exc

        try:
            if identify:
                await self.request(
                    "server.connection.identify",
                    {
                        "client_name": self.client_name,
                        "version": "0.1.0",
                        "type": "agent",
                    },
                )
        except Exception:
            await self.close()
            raise

    async def close(self) -> None:
        """Close the websocket connection."""

        ws = self._ws
        self._ws = None
        self._inbox.clear()
        self._messages.clear()
        if ws is not None:
            await ws.close()

    async def connect(self) -> None:
        """Compatibility alias for ``open``."""

        await self.open()

    async def disconnect(self) -> None:
        """Compatibility alias for ``close``."""

        await self.close()

    async def send(
        self,
        method: str,
        params: Mapping[str, JSON] | None = None,
        *,
        request_id: int | None = None,
    ) -> int:
        """Send one JSON-RPC request and return the request id."""

        ws = self._require_open()
        request_id = self._request_id() if request_id is None else request_id
        payload: dict[str, JSON] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = dict(params)

        try:
            await ws.send(json.dumps(payload))
        except Exception as exc:
            raise MoonrakerError(f"failed to send Moonraker request: {method}") from exc

        return request_id

    async def receive(self, *, request_id: int | None = None) -> dict[str, Any]:
        """Receive the next Moonraker message.

        When ``request_id`` is supplied, notifications and unrelated responses are
        skipped until the matching reply arrives.
        """

        if request_id is not None and request_id in self._inbox:
            return self._inbox.pop(request_id)

        if request_id is None and self._messages:
            return self._messages.pop(0)

        ws = self._require_open()
        while True:
            try:
                raw = await ws.recv()
            except Exception as exc:
                raise MoonrakerError("failed to receive Moonraker message") from exc

            message = self._decode(raw)
            if request_id is None or message.get("id") == request_id:
                return message

            other_id = message.get("id")
            if isinstance(other_id, int):
                self._inbox[other_id] = message
            else:
                self._messages.append(message)

    async def request(
        self,
        method: str,
        params: Mapping[str, JSON] | None = None,
    ) -> JSON:
        """Send one request and return its ``result`` value."""

        async with self._lock:
            request_id = await self.send(method, params)
            response = await self.receive(request_id=request_id)

        if "error" in response:
            raise MoonrakerError(self._format_error(response["error"]))
        return response.get("result")

    async def gcode(self, script: str) -> JSON:
        """Run one Klipper gcode script through Moonraker."""

        return await self.request("printer.gcode.script", {"script": script})

    async def send_gcode(self, script: str) -> JSON:
        """Compatibility alias for older component code."""

        return await self.gcode(script)

    async def wait_ready(
        self,
        *,
        timeout_s: float = 30.0,
        poll_interval_s: float = 0.25,
    ) -> None:
        """Wait until Moonraker reports Klippy is ready."""

        if self._ws is None:
            await self.open()

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s

        while True:
            state = await self.klippy_state()
            if state == "ready":
                return

            if loop.time() >= deadline:
                raise MoonrakerError(f"Klippy did not become ready; last state was {state!r}")

            await asyncio.sleep(poll_interval_s)

    async def klippy_state(self) -> str | None:
        """Return the current Klippy state from ``server.info``."""

        result = await self.request("server.info")
        if isinstance(result, dict):
            state = result.get("klippy_state")
            if isinstance(state, str):
                return state
        return None

    async def __aenter__(self) -> MoonrakerClient:
        await self.open()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    def _require_open(self) -> Any:
        if self._ws is None:
            raise MoonrakerError("Moonraker websocket is not open")
        return self._ws

    def _request_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _decode(self, raw: str | bytes) -> dict[str, Any]:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MoonrakerError(f"invalid JSON from Moonraker: {raw!r}") from exc

        if not isinstance(message, dict):
            raise MoonrakerError(f"unexpected Moonraker message: {message!r}")

        return message

    def _format_error(self, error: Any) -> str:
        if not isinstance(error, dict):
            return f"Moonraker error: {error!r}"

        code = error.get("code")
        message = error.get("message", "unknown Moonraker error")
        data = error.get("data")
        if data is None:
            return f"Moonraker error {code}: {message}"
        return f"Moonraker error {code}: {message} ({data!r})"


KlipperWebSocket = MoonrakerClient
