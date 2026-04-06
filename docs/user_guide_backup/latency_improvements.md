
---

## Phase 3 — Isolate a CPU Core for Klippy

The Pi 5 has 4 cores. Isolating core 3 from the Linux scheduler and dedicating it to Klippy dramatically reduces worst-case latency spikes from OS scheduling jitter.

```bash
# /boot/firmware/cmdline.txt
# Append to the EXISTING single line — do not add a newline
isolcpus=3 rcu_nocbs=3 nohz_full=3
```

> **Single line only.** `cmdline.txt` must remain one continuous line. A newline will prevent the Pi from booting.

Create a systemd override to pin Klippy to core 3 with real-time priority:

```bash
sudo systemctl edit klipper
```

```ini
[Service]
Nice=-15
CPUSchedulingPolicy=fifo
CPUSchedulingPriority=50
ExecStartPre=/bin/bash -c 'taskset -cp 3 $$BASHPID || true'
```

```bash
sudo systemctl daemon-reload
sudo reboot
```

Verify after reboot:

```bash
cat /sys/devices/system/cpu/isolated   # expected: 3
ps -eo pid,psr,comm | grep klippy      # PSR column should show 3
```

---

## Phase 5 — Patch `toolhead.py`

This is the key latency patch. Reducing the look-ahead flush threshold from the default ~250 ms to 10 ms eliminates buffering overhead for the discrete point-to-point moves a liquid handler makes.

```bash
# Back up first
cp ~/klipper/klippy/toolhead.py ~/klipper/klippy/toolhead.py.bak

# Find the constants — line numbers shift between Klipper versions
grep -n "BUFFER_TIME" ~/klipper/klippy/toolhead.py
grep -n "flush\|FLUSH\|lookahead\|junction" ~/klipper/klippy/toolhead.py | head -30
```

Apply these values:

```python
BUFFER_TIME_LOW  = 0.050   # was 1.0   — minimum MCU buffer depth
BUFFER_TIME_HIGH = 0.150   # was 2.0   — target MCU buffer depth
MOVE_BATCH_TIME  = 0.010   # was 0.500 — look-ahead batch window

# Also reduce the junction flush threshold (name varies by version):
# LOOKAHEAD_FLUSH_TIME = 0.010
# self.junction_flush  = 0.010
```

> **Risk.** A thinner MCU step buffer is safe for slow, discrete liquid handler moves. If you see mid-move hesitation, increase `BUFFER_TIME_LOW` back toward `0.100`.

```bash
sudo systemctl restart klipper
journalctl -u klipper -f    # watch for errors — Ctrl+C to exit
```
