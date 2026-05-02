"""Motion planning and probing helpers built on Moonraker RPC."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from .config import MotionConfig
from .exceptions import MotionError
from .protocols import JSONValue, NotificationMessage, RPCClient

_PROBE_PATTERN = re.compile(r"(?i)(?:result is z=|probe at .*? is z=)(-?\d+(?:\.\d+)?)")


@dataclass(slots=True)
class _QueuedMove:
    """Internal representation of a queued motion command."""

    axes: dict[str, float]
    speed: float
    wait: bool
    future: asyncio.Future[None]


class MotionController:
    """Translate motion requests into Moonraker G-code calls."""

    def __init__(self, client: RPCClient, config: MotionConfig) -> None:
        """Initialise the controller with an RPC client and motion defaults."""

        self._client = client
        self._config = config
        self._queue: list[_QueuedMove] = []
        self._queue_lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._status_subscription_ready = False
        self._print_state: str | None = None
        self._probe_lock = asyncio.Lock()

    async def home(self, axes: str = "XYZ") -> None:
        """Home the requested axes."""

        await self._flush_pending()
        target_axes = axes.strip().upper()
        command = "G28" if not target_axes else f"G28 {target_axes}"
        await self._send_script(command)
        await self.wait_for_idle()

    async def move(
        self,
        *,
        speed: float | None = None,
        wait: bool = True,
        **axes: float,
    ) -> None:
        """Queue a move and coalesce it with nearby requests."""

        if not axes:
            return

        normalised_axes = {axis.strip().upper(): value for axis, value in axes.items()}
        velocity = speed if speed is not None else self._config.default_speed_mm_s
        if velocity <= 0:
            raise MotionError("move speed must be greater than zero")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        queued_move = _QueuedMove(
            axes=normalised_axes,
            speed=velocity,
            wait=wait,
            future=future,
        )

        async with self._queue_lock:
            self._queue.append(queued_move)
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._delayed_flush())

        await future

    async def wait_for_idle(
        self,
        timeout_s: float = 10.0,
        poll_interval_s: float = 0.05,
    ) -> None:
        """Wait until Klipper reports `print_stats.state == "standby"`."""

        if timeout_s <= 0:
            raise MotionError("idle timeout must be greater than zero")

        await self._ensure_status_subscription()
        deadline = asyncio.get_running_loop().time() + timeout_s

        while True:
            if self._print_state == "standby":
                return

            response = await self._client.rpc(
                "printer.objects.query",
                {"objects": {"print_stats": ["state"]}},
            )
            state = self._extract_print_state(response)
            if state == "standby":
                self._print_state = state
                return

            if asyncio.get_running_loop().time() >= deadline:
                raise MotionError("timed out while waiting for idle motion state")

            await asyncio.sleep(poll_interval_s)

    async def probe_z(self, *, timeout_s: float = 10.0) -> float:
        """Run the configured `PROBE` macro and parse the reported Z height."""

        if timeout_s <= 0:
            raise MotionError("probe timeout must be greater than zero")

        await self._flush_pending()

        async with self._probe_lock:
            queue: asyncio.Queue[str] = asyncio.Queue()

            async def listener(message: NotificationMessage) -> None:
                """Capture gcode-response lines for probe parsing."""

                for line in self._extract_gcode_response_lines(message):
                    await queue.put(line)

            self._client.add_notification_listener("notify_gcode_response", listener)
            try:
                await self._send_script("PROBE")

                deadline = asyncio.get_running_loop().time() + timeout_s
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        raise MotionError("timed out while waiting for probe result")

                    response_line = await asyncio.wait_for(queue.get(), timeout=remaining)
                    match = _PROBE_PATTERN.search(response_line)
                    if match is None:
                        continue

                    await self.wait_for_idle(timeout_s=timeout_s)
                    return float(match.group(1))
            finally:
                self._client.remove_notification_listener("notify_gcode_response", listener)

    async def _delayed_flush(self) -> None:
        """Delay briefly to allow nearby moves to coalesce."""

        await asyncio.sleep(self._config.coalesce_window_ms / 1000.0)
        await self._flush_queue()

    async def _flush_queue(self) -> None:
        """Send the current queue as a single script call."""

        async with self._queue_lock:
            queued_moves = self._queue
            self._queue = []
            self._flush_task = None

        if not queued_moves:
            return

        script = "\n".join(self._format_move_command(move.axes, move.speed) for move in queued_moves)
        should_wait = any(move.wait for move in queued_moves)

        try:
            await self._send_script(script)
            if should_wait:
                await self.wait_for_idle()
        except Exception as exc:
            wrapped = exc if isinstance(exc, MotionError) else MotionError(str(exc))
            for move in queued_moves:
                if not move.future.done():
                    move.future.set_exception(wrapped)
            return

        for move in queued_moves:
            if not move.future.done():
                move.future.set_result(None)

    async def _flush_pending(self) -> None:
        """Wait for the active coalescing timer to flush."""

        task = self._flush_task
        if task is None:
            return
        await task

    async def _send_script(self, script: str) -> JSONValue:
        """Send a G-code script via Moonraker."""

        return await self._client.rpc("printer.gcode.script", {"script": script})

    def _format_move_command(self, axes: dict[str, float], speed: float) -> str:
        """Render a queued move as `G0`, `G1`, or `FORCE_MOVE`."""

        cartesian_axes = {"X", "Y", "Z", "E"}
        axis_names = set(axes)
        feedrate = speed * 60.0

        if axis_names.issubset(cartesian_axes):
            command = "G1" if "E" in axis_names else "G0"
            rendered_axes = " ".join(f"{axis}{value:.3f}" for axis, value in axes.items())
            return f"{command} {rendered_axes} F{feedrate:.3f}"

        if len(axes) != 1:
            raise MotionError("FORCE_MOVE only supports a single non-cartesian axis per command")

        axis, distance = next(iter(axes.items()))
        if axis in cartesian_axes:
            raise MotionError("mixed cartesian and force-move axes are not supported")
        return (
            f"FORCE_MOVE STEPPER=stepper_{axis.lower()} "
            f"DISTANCE={distance:.6f} VELOCITY={speed:.6f}"
        )

    async def _ensure_status_subscription(self) -> None:
        """Enable status updates used by `wait_for_idle`."""

        if self._status_subscription_ready:
            return

        self._client.add_notification_listener("notify_status_update", self._handle_status_update)
        await self._client.subscribe_objects({"print_stats": ["state"]})
        self._status_subscription_ready = True

    async def _handle_status_update(self, message: NotificationMessage) -> None:
        """Track the latest `print_stats.state` pushed by Moonraker."""

        params = message.get("params")
        if not isinstance(params, list) or not params:
            return
        status_payload = params[0]
        if not isinstance(status_payload, dict):
            return
        print_stats = status_payload.get("print_stats")
        if not isinstance(print_stats, dict):
            return
        state = print_stats.get("state")
        if isinstance(state, str):
            self._print_state = state

    def _extract_print_state(self, response: JSONValue) -> str | None:
        """Extract `print_stats.state` from a `printer.objects.query` response."""

        if not isinstance(response, dict):
            return None
        status = response.get("status")
        if not isinstance(status, dict):
            return None
        print_stats = status.get("print_stats")
        if not isinstance(print_stats, dict):
            return None
        state = print_stats.get("state")
        if isinstance(state, str):
            return state
        return None

    def _extract_gcode_response_lines(self, message: NotificationMessage) -> list[str]:
        """Extract text lines from a `notify_gcode_response` notification."""

        params = message.get("params")
        if not isinstance(params, list):
            return []

        lines: list[str] = []
        for item in params:
            if isinstance(item, str):
                lines.append(item)
            elif isinstance(item, list):
                lines.extend(part for part in item if isinstance(part, str))
        return lines
