#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: High-level gantry movement controls backed by Moonraker G-code requests.
"""
from typing import Any
from klipper_lh.moonraker import MoonrakerClient
from klipper_lh.devices import MoonrakerDevice

# ──── Constants ──────────────────────────────────────────────────────────────────────────────────────
MIN_STEPPER_CURRENT = 0.10
MAX_STEPPER_CURRENT = 1.00
DEFAULT_MOVE_TIMEOUT = 180.0
QueryObjects = dict[str, Any]

# ──── Pump Class ─────────────────────────────────────────────────────────────────────────────────────
class Pump(MoonrakerDevice):
    """Higher level class to control the syringe pump that operates through the moonraker client."""

    def __init__(self, client: MoonrakerClient, name: str = "Pump") -> None:
        super().__init__(client=client, name=name)
        self._flr: float = 0
        self._diam: float = 0
        self._max_flr: float = 50
        self._max_vol: float = 1000

    # ──── Pump Properties ───────────────────────────────────────────────────────────────────────────────
    @property
    def flow_rate(self)-> float:
        return self._flr

    @flow_rate.setter
    def flow_rate(self, value: float | int | str):
        try:
            _flr =  float(value)
        except ValueError as e:
            raise ValueError("Failed to coerce given flow rate to float") from e
        if _flr < 0.0:
            self.log.warning("Given flow rate below usable range; clamping to 0")
            _flr = 0
        self._flr = _flr

    @property
    def diameter(self) -> float:
        return self._flr

    @diameter.setter
    def diameter(self, value: float | int | str):
        try:
            diam = float(value)
        except ValueError as e:
            raise ValueError("Failed to coerce given diameter to float") from e
        self._diam = diam

    # ──── Pump Actions ───────────────────────────────────────────────────────────────────────────────
    async def aspirate(self, volume: float, flow_rate: float, power: float) -> None:
        pass

    async def dispense(self,volume: float, flow_rate: float, power: float) -> None:
        pass

    async def refill(self) -> None:
        pass

    async def empty(self) -> None:
        pass

    # ──── Internals ──────────────────────────────────────────────────────────────────────────────────
    async def _get_scaled_current(self, power: float) -> float:
        """Scale stepper current from a normalized power value between 0 and 1."""
        if power > MAX_STEPPER_CURRENT or power < MIN_STEPPER_CURRENT:
            self.log.warning("Given power value outside usable range; clamping to min/max limit")
        clamped_power = max(MIN_STEPPER_CURRENT, min(power, MAX_STEPPER_CURRENT))
        return MIN_STEPPER_CURRENT + clamped_power * (MAX_STEPPER_CURRENT - MIN_STEPPER_CURRENT)

    async def _set_tmc_current(self, stepper: str, current: float = MAX_STEPPER_CURRENT) -> None:
        """Set the configured current for one TMC-backed stepper."""
        await self.send_command(f"SET_TMC_CURRENT STEPPER={stepper} CURRENT={current}")