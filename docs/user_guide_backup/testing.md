
## Phase 9 — Verify and Benchmark

**Functional test sequence:**

1. `journalctl -u klipper -f` — watch for startup errors
2. Open Mainsail at `http://192.168.10.2` — confirm state shows **Ready**
3. Run `G28 X Y` — confirm both CoreXY motors move and home
4. `SET_KINEMATIC_POSITION X=0 Y=0 Z=0` then `G1 X10 F600` — verify motion
5. Confirm direct Ethernet latency before tuning further

**Expected latency after full tuning:**

| Configuration                   | Latency   |
|---------------------------------|-----------|
| Baseline Klipper (HTTP)         | ~350 ms   |
| WebSocket only                  | ~250 ms   |
| WebSocket + `toolhead.py` patch | ~40 ms    |
| + CPU isolation (median)        | ~15–20 ms |

> **Target achieved.** With all three optimisations active, median dispatch latency sits at 15–20 ms — appropriate for liquid handling workflows where individual moves take hundreds of milliseconds.

---

## Notes

- This setup intentionally trades motion buffering for responsiveness.
- Timing values are appropriate for a slow, discrete liquid handler — not a high-speed 3D printer.
- If the machine stutters during motion, relax `BUFFER_TIME_LOW` slightly toward `0.100`.
