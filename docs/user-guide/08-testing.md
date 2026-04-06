# Testing and Bring-Up

> This section confirms that the full stack is working: Raspberry Pi, Octopus firmware, Klipper configuration, Moonraker, and basic machine motion.


## Before You Start

Only begin testing when:

- the Pi is reachable at `192.168.10.2`
- Mainsail loads in the browser
- Klipper starts without configuration errors
- the machine is safe to move

Before sending any motion command:

- make sure the carriage can move freely
- keep a hand near the power switch or emergency stop
- verify the endstops are installed and wired as expected
- keep tools, cables, and fingers clear of the motion path

---

## Step 1 - Watch the Klipper Log

Open an SSH session to the Pi and follow the Klipper log:

```bash
journalctl -u klipper -f
```

Leave this running while you perform the first tests. If something goes wrong, the log usually explains it immediately.

---

## Step 2 - Confirm the UI Reaches the Machine

On the controller PC, open:

```text
http://192.168.10.2
```

In Mainsail, confirm that the printer state becomes **Ready**.

If it does not:

- refresh the page
- check the Klipper log
- check the Moonraker log with `journalctl -u moonraker -f`

Do not continue to motion testing until the UI reports a healthy connection.

---

## Step 3 - Check Endstop State Before Homing

In the Mainsail console, query the endstop inputs:

```text
QUERY_ENDSTOPS
```

Confirm the reported state makes sense for your machine before you home any axis.

This is a simple but important safety check. If an endstop is stuck in the triggered state or wired to the wrong pin, homing can behave unpredictably.

---

## Step 4 - Home Carefully

Home the motion system in a controlled order.

Recommended first sequence:

```text
G28 X
G28 Y
```

If your Z setup is ready and safe, then:

```text
G28 Z
```

Watch for:

- the correct motors moving
- motion in the correct direction
- each axis stopping on the correct endstop

Stop immediately if:

- the wrong axis moves
- the axis moves away from the endstop during homing
- the motor drives into a hard stop

---

## Step 5 - Test a Small Controlled Move

Once homing is confirmed, issue a small move:

```text
SET_KINEMATIC_POSITION X=0 Y=0 Z=0
G1 X10 F600
```

This checks that:

- the machine accepts manual G-code
- the motion system responds predictably
- the X axis moves a small known distance without faulting

You can repeat similarly small moves on the other axes once the first move looks correct.

---

## Step 6 - Test the API Path

At this point the browser path is working. The next thing to confirm is that Moonraker is reachable for software control as well.

A minimal check is simply that Mainsail remains connected and responsive while commands are sent. If you are using the Python tools in this repository, this is the stage where you can run a basic session or client connectivity check.

---

## Step 7 - Evaluate Latency

If you applied the optional tuning in [Latency Improvements](07-latency-improvements.md), compare your observed behaviour against the expected ranges:

| Configuration | Approximate Latency |
| --- | --- |
| Baseline Klipper over HTTP | `~350 ms` |
| WebSocket only | `~250 ms` |
| WebSocket + `toolhead.py` patch | `~40 ms` |
| WebSocket + patch + CPU isolation | `~15-20 ms` median |

The key practical question is not whether the number is perfect, but whether the liquid handler responds quickly and consistently enough for the intended workflow.

---

## Common Problems

| Symptom | Likely Cause |
| --- | --- |
| Mainsail loads but printer is not ready | `printer.cfg` or `moonraker.conf` still contains an error |
| No `/dev/serial/by-id/` device | firmware did not flash correctly, or the board is not powered properly |
| Wrong motor moves during homing | stepper pins or axis mapping in `printer.cfg` are incorrect |
| Axis moves the wrong direction | motor direction pin or inversion needs adjusting |
| Motion stutters after low-latency tuning | buffer values are too aggressive for the current machine |

---

## Done

You should now have:

- a flashed and reachable Octopus
- a Pi running Klipper, Moonraker, and Mainsail
- a working `printer.cfg`
- a direct-Ethernet control link
- a machine that can be brought to a safe, testable ready state

From here you can move on to machine-specific calibration, software integration, and higher-level liquid-handling workflows.

---

## Navigation

- Previous: [Latency Improvements](07-latency-improvements.md)
- Index: [Klipper Setup Guide](../index.md)
