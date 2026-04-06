
## Phase 7 — `printer.cfg`

Create `~/printer_data/config/printer.cfg` via Mainsail's editor or directly on the Pi. Adjust motor currents, axis limits, lead screw pitch, and syringe calibration for your machine.

```ini
# ============================================================
# CoreXY Liquid Handler — BTT Octopus + TMC2209
# Low-latency config — patched toolhead, direct WebSocket
# ============================================================

[mcu]
serial: /dev/serial/by-id/usb-Klipper_stm32f446xx_XXXXXXXX-if00
restart_method: command

[printer]
kinematics: corexy
max_velocity: 300
max_accel: 3000          # conservative until input shaper calibrated
max_z_velocity: 20
max_z_accel: 200
minimum_cruise_ratio: 0  # don't require cruise phase for short moves
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
rotation_distance: 8     # adjust for your lead screw pitch
endstop_pin: ^PG10
position_endstop: 0
position_min: -5
position_max: 200

[tmc2209 stepper_z]
uart_pin: PC6
run_current: 0.600
stealthchop_threshold: 999999

# ---- Syringe / pipette axis (MOTOR3) ------------------------
# Mapped as extruder since Klipper requires one
[extruder]
step_pin: PG4
dir_pin: PC1
enable_pin: !PA0
microsteps: 16
rotation_distance: 8     # tune for your syringe mechanism
nozzle_diameter: 1.0     # unused — required field
filament_diameter: 1.75  # unused — required field
heater_pin: PA2          # unused — disable heater
sensor_type: Generic 3950
sensor_pin: PF4
min_temp: -50            # disable thermal protection
max_temp: 300

[tmc2209 extruder]
uart_pin: PC7
run_current: 0.600
stealthchop_threshold: 999999

# ---- LLD probe (capacitive or conductivity sensor) ----------
[probe]
pin: ^PG12               # wire your LLD digital output here
x_offset: 0
y_offset: 0
z_offset: 0
speed: 3                 # mm/s descent speed during probe
lift_speed: 10
samples: 1
sample_retract_dist: 2.0
samples_tolerance: 0.05

# ---- Max endstop safety switches ----------------------------
[gcode_button x_max]
pin: ^PG13
press_gcode:
    M112                 # emergency stop on overtravel

[gcode_button y_max]
pin: ^PG14
press_gcode:
    M112

# ---- Required infrastructure --------------------------------
[virtual_sdcard]
path: ~/printer_data/gcodes

[display_status]
[pause_resume]

# ---- LH protocol macros -------------------------------------
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