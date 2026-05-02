#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: High-level gantry movement controls backed by Moonraker G-code requests.
"""

from __future__ import annotations

import asyncio
import math
import time

from klipper_lh.exceptions import MotionError
from klipper_lh.moonraker import MoonrakerClient
from klipper_lh.devices import MoonrakerDevice


# ──── Constants ──────────────────────────────────────────────────────────────────────────────────────
MIN_STEPPER_CURRENT = 0.10
MAX_STEPPER_CURRENT = 1.00
DEFAULT_MOVE_TIMEOUT = 180.0
POSITION_TOLERANCE = 0.001
DEFAULT_MOVE_SPEED = 20.0
AxisPosition = dict[str, float]
_AXES = ("X", "Y", "Z", "E")
_LIVE_POSITION_AXIS_MAP = {"X": 0, "Y": 1, "Z": 2, "E": 3}


# ──── Gantry Class ───────────────────────────────────────────────────────────────────────────────────
class Gantry(MoonrakerDevice):
    """Convenience wrapper for gantry-specific Moonraker operations.

    The class keeps Moonraker request details out of higher-level liquid
    handling code. It sends G-code through ``printer.gcode.script`` and reads
    motion state through ``printer.objects.query``.
    """

    def __init__(self, client: MoonrakerClient, name: str = "Gantry") -> None:
        super().__init__(client=client, name=name)
        self._move_lock = asyncio.Lock()

    # ──── Info Retrieval ──────────────────────────────────────────────────────────────────────────────
    async def get_target_position(self) -> AxisPosition:
        """Return the current commanded G-code position keyed by axis."""
        response = await self.send_query(query="gcode_move")
        status = response["status"]["gcode_move"]
        position_by_axis = {
            axis: status["position"][axis_index]
            for axis, axis_index in status["axis_map"].items()
        }
        self.log.debug(f"Received: {status} to build: {position_by_axis}")
        return position_by_axis

    async def get_current_position(self) -> AxisPosition:
        """Return the live motion-report position keyed by axis."""
        response = await self.send_query(query="motion_report")
        status = response["status"]["motion_report"]
        position_by_axis = {
            axis: status["live_position"][axis_index]
            for axis, axis_index in _LIVE_POSITION_AXIS_MAP.items()
        }
        self.log.debug(f"Received: {status} to build: {position_by_axis}")
        return position_by_axis


    # ──── Waiting ─────────────────────────────────────────────────────────────────────────────────────
    async def wait_for_move(
        self,
        timeout: float = DEFAULT_MOVE_TIMEOUT,
        tol: float = POSITION_TOLERANCE,
    ) -> None:
        """Poll live position until it reaches the current G-code target."""
        target_position = await self.get_target_position()
        current_position = await self.get_current_position()
        start_time = time.monotonic()

        while (
            not self._positions_close(target_position, current_position, tol=tol)
            and (time.monotonic() - start_time) < timeout
        ):
            current_position = await self.get_current_position()
            await asyncio.sleep(0.1)

    @staticmethod
    def _positions_close(
        target_position: AxisPosition,
        current_position: AxisPosition,
        tol: float = POSITION_TOLERANCE,
    ) -> bool:
        """Return True when all tracked axes are within tolerance."""
        for axis in _AXES:
            if not math.isclose(target_position[axis], current_position[axis], abs_tol=tol):
                return False
        return True


    # ──── Gantry actions ──────────────────────────────────────────────────────────────────────────────
    async def home(self, debug: bool = False) -> None:
        """Home the gantry, optionally bypassing physical homing for debugging."""
        self.log.debug(f"Homing Gantry with debug bypass set to: {debug}")

        command = "SET_KINEMATIC_POSITION X=0 Y=0 Z=0" if debug else "G28"
        response = await self.send_command(command)

        if response != "ok":
            raise MotionError(f"Failed to home gantry with response: {response}")

        self.log.debug(f"Gantry homing complete with response: {response}")

    async def move(
        self,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        speed: float = DEFAULT_MOVE_SPEED,
        power: float = 1.0,
        timeout: float = DEFAULT_MOVE_TIMEOUT,
    ) -> None:
        """Move to the requested coordinate.

        XY and Z moves are sent separately so a horizontal move cannot drag the
        toolhead through the deck before a Z correction has completed.
        """
        async with self._move_lock:
            await self._move_xy(x=x, y=y, speed=speed, power=power, timeout=timeout)
            await self._move_z(z=z, speed=speed, power=power, timeout=timeout)

    async def _move_xy(
        self,
        x: float | None = None,
        y: float | None = None,
        speed: float = DEFAULT_MOVE_SPEED,
        power: float = 1.0,
        timeout: float = DEFAULT_MOVE_TIMEOUT,
    ) -> None:
        """Move to an X/Y coordinate while leaving Z unchanged."""
        position_parts: list[str] = []
        if x is not None:
            position_parts.append(f"X{x:.3f}")
        if y is not None:
            position_parts.append(f"Y{y:.3f}")
        if not position_parts:
            return

        position = " ".join(position_parts)
        self.log.debug(f"Moving to XY position {position}")

        stepper_current = await self._get_scaled_current(power=power)
        await self._set_tmc_current(stepper="stepper_x", current=stepper_current)
        await self._set_tmc_current(stepper="stepper_y", current=stepper_current)

        await self.send_command(f"G0 {position} F{speed * 60}")
        await self.wait_for_move(timeout=timeout)

    async def _move_z(
        self,
        z: float | None = None,
        speed: float = DEFAULT_MOVE_SPEED,
        power: float = 1.0,
        timeout: float = DEFAULT_MOVE_TIMEOUT,
    ) -> None:
        """Move to a Z coordinate while leaving X/Y unchanged."""
        if z is None:
            return

        position = f"Z{z:.3f}"
        self.log.debug(f"Moving to Z position {position}")

        stepper_current = await self._get_scaled_current(power=power)
        await self._set_tmc_current(stepper="stepper_z", current=stepper_current)
        await self.send_command(f"G0 {position} F{speed * 60}")
        await self.wait_for_move(timeout=timeout)

    async def enable_motors(self) -> None:
        """Energise all gantry motors."""
        await self.send_command("M17")
        self.log.debug("Enabled gantry motors")

    async def disable_motors(self) -> None:
        """De-energise all gantry motors."""
        await self.send_command("M18")
        self.log.debug("Enabled gantry motors")


    # ──── Internals ───────────────────────────────────────────────────────────────────────────────────
    async def _get_scaled_current(self, power: float) -> float:
        """Scale stepper current from a normalized power value between 0 and 1."""
        if power > 1.0 or power < 0.0:
            self.log.warning("Given power value outside usable range; clamping to min/max limit")

        clamped_power = max(0.0, min(power, 1.0))
        return MIN_STEPPER_CURRENT + clamped_power * (MAX_STEPPER_CURRENT - MIN_STEPPER_CURRENT)

    async def _set_tmc_current(self, stepper: str, current: float = MAX_STEPPER_CURRENT) -> None:
        """Set the configured current for one TMC-backed stepper."""
        await self.send_command(f"SET_TMC_CURRENT STEPPER={stepper} CURRENT={current}")
