# Latency Improvements

> This section details the optional tuning improvements to reduce command-to-motion latency.

This chapter covers two improvements:

1. Isolating one Raspberry Pi CPU core for Klippy
2. Reducing Klipper's look-ahead buffering in `toolhead.py`

Together, these changes reduce scheduler jitter and shorten the amount of motion queued ahead of time. That is useful for a liquid handler because it typically performs shorter, more discrete moves than a 3D printer.

> These settings are appropriate for a controlled liquid-handling workflow. They are not recommended as a default tuning profile for a general-purpose high-speed 3D printer.

---

## ! Before Changing Anything !

These changes are **optional**. Apply them only after:

- the Octopus is flashed correctly
- `printer.cfg` loads
- Moonraker is reachable
- the machine can home and execute basic motion safely

That order matters. It is much easier to debug a standard Klipper setup first and then optimise it than it is to debug a broken baseline plus low-latency patches at the same time.

---
## Step 1 - Isolate a CPU Core for Klippy

The Raspberry Pi 5 has four CPU cores. A straightforward latency improvement is to isolate one core from the normal Linux scheduler and pin Klippy to it.

Open the Pi boot command line:

```bash
sudo nano /boot/firmware/cmdline.txt
```

Append the following text to the **existing single line**:

```text
isolcpus=3 rcu_nocbs=3 nohz_full=3
```

> `cmdline.txt` must remain one continuous line. Do not insert a newline.

Now create a systemd override for Klipper:

```bash
sudo systemctl edit klipper
```

Add:

```ini
[Service]
Nice=-15
CPUSchedulingPolicy=fifo
CPUSchedulingPriority=50
ExecStartPre=/bin/bash -c 'taskset -cp 3 $$BASHPID || true'
```

Then reload systemd and reboot:

```bash
sudo systemctl daemon-reload
sudo reboot
```

---

## Step 2 - Verify CPU Isolation

After the Pi comes back online, reconnect over SSH and check the result:

```bash
cat /sys/devices/system/cpu/isolated
ps -eo pid,psr,comm | grep klippy
```

Expected results:

- `/sys/devices/system/cpu/isolated` should report `3`
- the `PSR` column for `klippy` should also show `3`

If that is not true, fix the CPU isolation step before moving on.

---

## Step 3 - Back Up and Patch `toolhead.py`

The second optimisation is to reduce Klipper's motion look-ahead timing.

Back up the file first:

```bash
cp ~/klipper/klippy/toolhead.py ~/klipper/klippy/toolhead.py.bak
```

Now locate the relevant timing constants:

```bash
grep -n "BUFFER_TIME" ~/klipper/klippy/toolhead.py
grep -n "flush\|FLUSH\|lookahead\|junction" ~/klipper/klippy/toolhead.py | head -30
```

The exact line numbers can vary by Klipper version. Use the search output you just generated rather than assuming fixed line numbers.

Change the values to approximately:

```python
BUFFER_TIME_LOW  = 0.050
BUFFER_TIME_HIGH = 0.150
MOVE_BATCH_TIME  = 0.010
```

Also reduce the look-ahead or junction flush threshold if present. Depending on your Klipper version it may appear as one of the following:

```python
LOOKAHEAD_FLUSH_TIME = 0.010
```

or:

```python
self.junction_flush = 0.010
```

---

## Step 4 - Restart Klipper and Verify Stability

Apply the change:

```bash
sudo systemctl restart klipper
journalctl -u klipper -f
```

Watch the log for startup errors. If the service starts normally, test a few simple moves before continuing to production use.

---

## What Improvement to Expect

Typical command latency figures from this setup are:

| Configuration                           | Approximate Latency   |
|-----------------------------------------|-----------------------|
| Baseline Klipper over HTTP              | `~350 ms`             |
| WebSocket only                          | `~250 ms`             |
| WebSocket plus `toolhead.py` patch      | `~40 ms`              |
| WebSocket plus patch plus CPU isolation | `~15-20 ms` median    |

These figures are directionally useful rather than guaranteed. The exact result depends on the Pi load, network path, and how the control software talks to Moonraker.

---

## Rollback and Safety Notes

If motion becomes hesitant or unstable after the patch:

- restore the backup of `toolhead.py`, or
- increase `BUFFER_TIME_LOW` gradually toward `0.100`

If the Pi fails to boot after the CPU isolation change:

- re-check `/boot/firmware/cmdline.txt`
- make sure the added kernel parameters are still on one line

The goal is lower latency, not aggressive tuning for its own sake. If the baseline machine is stable and responsive enough for your workflow, you may choose to skip this section entirely.

---

## Next Step

Continue to [Testing and Bring-Up](08-testing.md).

---

## Navigation

- Previous: [Moonraker Configuration](06-moonraker-config.md)
- Index: [Klipper Setup Guide](../index.md)
- Next: [Testing and Bring-Up](08-testing.md)
