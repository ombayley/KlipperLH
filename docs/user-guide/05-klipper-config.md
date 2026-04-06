# Klipper Configuration

> By the end of this section, you will have a working `printer.cfg` for the liquid handler and Klipper will be able to start against the flashed Octopus.

---

## At a Glance

| Item | Value |
| --- | --- |
| Goal | Create the machine-specific Klipper configuration file |
| Estimated time | 20 to 30 minutes |
| You finish with | A loadable `printer.cfg` and a machine that can progress to ready state |

---

## What This Section Does

`printer.cfg` is the main Klipper configuration file. It defines:

- how Klipper talks to the MCU
- the machine kinematics
- stepper and driver pin mappings
- endstops and probe inputs
- macros for common liquid-handling operations

This chapter provides a full starting configuration for the CoreXY liquid handler platform used in this repository.

---

## Before You Start

Make sure:

- [Klipper Firmware Flashing](04-klipper-flash.md) is complete
- the Octopus appears under `/dev/serial/by-id/`
- you know which serial path belongs to your board

You will be editing:

```text
~/printer_data/config/printer.cfg
```

You can do that either:

- in the Mainsail file editor, or
- directly over SSH with a text editor such as `nano`

---

## Step 1 - Find the MCU Serial Path

List the serial devices on the Pi:

```bash
ls /dev/serial/by-id/
```

Copy the full device name for the Octopus. It will look similar to:

```text
usb-Klipper_stm32f446xx_XXXXXXXX-if00
```

You will paste that full path into the `[mcu]` section below.

---

## Step 2 - Create or Edit `printer.cfg`

Open the file:

```bash
nano ~/printer_data/config/printer.cfg
```

Then paste the configuration below and replace the example MCU serial path with your actual path from the previous step.

```ini
# ============================================================
# CoreXY Liquid Handler — BTT Octopus + TMC2209
# Direct Ethernet + Moonraker + optional low-latency tuning
# ============================================================

[mcu]
serial: /dev/serial/by-id/usb-Klipper_stm32f446xx_XXXXXXXX-if00
restart_method: command

[printer]
kinematics: corexy
max_velocity: 300
max_accel: 3000
max_z_velocity: 20
max_z_accel: 200
minimum_cruise_ratio: 0
square_corner_velocity: 5.0

# ---- CoreXY A motor (MOTOR0) --------------------------------
[stepper_x]
step_pin: PF13
dir_pin: PF12
enable_pin: !PF14
microsteps: 16
rotation_distance: 40
endstop_pin: ^PG6
position_endstop: 0
position_min: 0
position_max: 300
homing_speed: 50
homing_positive_dir: false

[tmc2209 stepper_x]
uart_pin: PC4
run_current: 0.800
stealthchop_threshold: 999999

# ---- CoreXY B motor (MOTOR1) --------------------------------
[stepper_y]
step_pin: PG0
dir_pin: !PG1
enable_pin: !PF15
microsteps: 16
rotation_distance: 40
endstop_pin: ^PG9
position_endstop: 0
position_min: 0
position_max: 300
homing_speed: 50
homing_positive_dir: false

[tmc2209 stepper_y]
uart_pin: PD11
run_current: 0.800
stealthchop_threshold: 999999

# ---- Z axis (MOTOR2_1) --------------------------------------
[stepper_z]
step_pin: PF11
dir_pin: PG3
enable_pin: !PG5
microsteps: 16
rotation_distance: 8
endstop_pin: ^PG10
position_endstop: 0
position_min: -5
position_max: 200

[tmc2209 stepper_z]
uart_pin: PC6
run_current: 0.600
stealthchop_threshold: 999999

# ---- Syringe / pipette axis (MOTOR3) ------------------------
# Mapped as an extruder because Klipper requires an extruder section
[extruder]
step_pin: PG4
dir_pin: PC1
enable_pin: !PA0
microsteps: 16
rotation_distance: 8
nozzle_diameter: 1.0
filament_diameter: 1.75
heater_pin: PA2
sensor_type: Generic 3950
sensor_pin: PF4
min_temp: -50
max_temp: 300

[tmc2209 extruder]
uart_pin: PC7
run_current: 0.600
stealthchop_threshold: 999999

# ---- Liquid-level detector probe -----------------------------
[probe]
pin: ^PG12
x_offset: 0
y_offset: 0
z_offset: 0
speed: 3
lift_speed: 10
samples: 1
sample_retract_dist: 2.0
samples_tolerance: 0.05

# ---- Max-travel safety switches ------------------------------
[gcode_button x_max]
pin: ^PG13
press_gcode:
    M112

[gcode_button y_max]
pin: ^PG14
press_gcode:
    M112

# ---- Required Klipper infrastructure -------------------------
[virtual_sdcard]
path: ~/printer_data/gcodes

[display_status]
[pause_resume]

# ---- Liquid-handler helper macros ----------------------------
[gcode_macro ASPIRATE_WELL]
gcode:
    {% set x      = params.X|float %}
    {% set y      = params.Y|float %}
    {% set vol    = params.VOL|float %}
    {% set safe_z = params.SAFE_Z|default(20)|float %}
    {% set asp_z  = params.ASP_Z|default(2)|float %}
    G1 X{x} Y{y} Z{safe_z} F{300*60}
    G1 Z{asp_z} F{20*60}
    G1 E-{vol * 0.1} F{5*60}
    G1 Z{safe_z} F{100*60}
    M400

[gcode_macro DISPENSE_WELL]
gcode:
    {% set x      = params.X|float %}
    {% set y      = params.Y|float %}
    {% set vol    = params.VOL|float %}
    {% set safe_z = params.SAFE_Z|default(20)|float %}
    {% set disp_z = params.DISP_Z|default(5)|float %}
    G1 X{x} Y{y} Z{safe_z} F{300*60}
    G1 Z{disp_z} F{20*60}
    G1 E{vol * 0.1} F{5*60}
    G1 Z{safe_z} F{100*60}
    M400

[gcode_macro PROBE_LIQUID]
gcode:
    {% set x        = params.X|float %}
    {% set y        = params.Y|float %}
    {% set search_z = params.SEARCH_Z|default(20)|float %}
    G1 X{x} Y{y} Z{search_z} F{200*60}
    PROBE
    M400
```

---

## Step 3 - Review the Values That Must Match Your Machine

Do not assume every value above is correct for your final build. Before treating the machine as production-ready, review at least the following:

| Setting Area | What to Check |
| --- | --- |
| `[mcu]` | the full serial path matches your Octopus |
| `[stepper_x]`, `[stepper_y]`, `[stepper_z]` | endstop pins, directions, and travel limits match your wiring and mechanics |
| `rotation_distance` | pulley / leadscrew / syringe calibration is correct |
| `run_current` | driver current is safe for your motors |
| `[probe]` | the liquid-level detector input pin matches your wiring |
| macros | any volume-to-motion conversion reflects the actual pipette mechanism |

The file above is a solid starting point, not a substitute for final machine-specific calibration.

---

## Step 4 - Restart Klipper

After saving `printer.cfg`, restart Klipper:

```bash
sudo systemctl restart klipper
```

If you are using Mainsail, refresh the page afterward.

---

## Check Your Work

At this stage you want:

- Klipper to start without configuration syntax errors
- Mainsail to stop showing a missing-config error
- the printer state to move closer to `Ready`

If Klipper fails to start, inspect the log:

```bash
journalctl -u klipper -f
```

Read the first reported configuration error carefully. It is usually a pin typo, serial-path mismatch, or unsupported field name.

---

## Next Step

Continue to [Moonraker Configuration](06-moonraker-config.md).

---

## Navigation

- Previous: [Klipper Firmware Flashing](04-klipper-flash.md)
- Index: [Klipper Setup Guide](../index.md)
- Next: [Moonraker Configuration](06-moonraker-config.md)
