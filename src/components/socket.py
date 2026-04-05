#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: O. Bayley
Description: **Add Desc**.
"""
import asyncio
import json
from dataclasses import dataclass, field
import websockets

@dataclass
class KlipperWebSocket:
    host: str
    _ws: any = field(default=None, init=False)
    _id: int = field(default=0, init=False)

    async def connect(self) -> None:
        self._ws = await websockets.connect(f"ws://{self.host}/websocket")

    async def send_gcode(self, cmd: str) -> None:
        self._id += 1
        payload = json.dumps({
            "id": self._id,
            "method": "gcode/script",
            "params": {"script": cmd}
        })
        await self._ws.send(payload)
        await self._ws.recv()  # wait for ack
