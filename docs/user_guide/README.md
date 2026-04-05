# KlipperLH

Klipper low-latency setup notes for a CoreXY liquid handler using a BTT Octopus, Raspberry Pi 5, Moonraker, and Mainsail.

## Overview

This setup is designed around:

- Raspberry Pi 5 running Raspberry Pi OS Lite
- BTT Octopus controller
- Klipper + Moonraker + Mainsail installed via KIAUH
- Direct Ethernet between the PC and Pi
- A patched Klipper `toolhead.py` to reduce look-ahead latency
- Optional CPU isolation on the Pi to reduce scheduling jitter

The target is a low-latency liquid handling system where discrete point-to-point moves matter more than sustained 3D-printing-style motion buffering.

## 1. Flash Raspberry Pi OS

Use Raspberry Pi Imager and select:

- Device: Raspberry Pi 5
- OS: Raspberry Pi OS Lite (64-bit)
- Hostname: `liquidhandler`
- Username: `pi`
- SSH: enabled
- Wi-Fi: leave unconfigured

After booting the Pi, connect over SSH and update packages:

```bash
ssh pi@liquidhandler.local
sudo apt update && sudo apt upgrade -y
sudo apt install git -y
```

## 2. Configure direct Ethernet

Set a static IP on the Pi by editing `/etc/dhcpcd.conf`:

```conf
interface eth0
static ip_address=192.168.10.2/24
static routers=192.168.10.1
```

Set the laptop Ethernet adapter to:

- IP address: `192.168.10.1`
- Subnet mask: `255.255.255.0`
- Gateway: `192.168.10.2` or blank

Verify connectivity:

```bash
ping 192.168.10.2
ssh pi@192.168.10.2
```

## 3. Isolate a CPU core for Klippy

Append this to the existing single line in `/boot/firmware/cmdline.txt`:

```text
isolcpus=3 rcu_nocbs=3 nohz_full=3
```

Do not add a newline. `cmdline.txt` must remain a single line.

Create a Klipper systemd override:

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

Then reload and reboot:

```bash
sudo systemctl daemon-reload
sudo reboot
```

Verify:

```bash
cat /sys/devices/system/cpu/isolated
ps -eo pid,psr,comm | grep klippy
```

Expected result: isolated core `3`, and `klippy` pinned to processor `3`.

## 4. Install Klipper, Moonraker, and Mainsail

Install with KIAUH:

```bash
cd ~
git clone https://github.com/dw-0/kiauh.git
./kiauh/kiauh.sh
```

Install in this order:

1. Klipper
2. Moonraker
3. Mainsail

Once complete, Mainsail should be reachable at [http://192.168.10.2](http://192.168.10.2).

## 5. Patch Klipper look-ahead timing

This is the key low-latency change. Back up and inspect `~/klipper/klippy/toolhead.py`:

```bash
cp ~/klipper/klippy/toolhead.py ~/klipper/klippy/toolhead.py.bak
grep -n "BUFFER_TIME" ~/klipper/klippy/toolhead.py
grep -n "flush\|FLUSH\|lookahead\|LOOKAHEAD\|junction" ~/klipper/klippy/toolhead.py | head -30
```

Update the timing constants to approximately:

```python
BUFFER_TIME_LOW = 0.050
BUFFER_TIME_HIGH = 0.150
MOVE_BATCH_TIME = 0.010
```

Also reduce the look-ahead flush threshold if present, for example:

```python
LOOKAHEAD_FLUSH_TIME = 0.010
```

or:

```python
self.junction_flush = 0.010
```

Restart Klipper afterward:

```bash
sudo systemctl restart klipper
journalctl -u klipper -f
```

If you see mid-move hesitation, increase `BUFFER_TIME_LOW` toward `0.100`.

## 6. Build and flash the Octopus firmware

From the Pi:

```bash
cd ~/klipper
make menuconfig
```

Use these settings:

- Architecture: `STMicroelectronics STM32`
- Processor model: `STM32F446`
- Bootloader offset: `32KiB bootloader`
- Clock reference: `12 MHz crystal`
- Communication interface: `USB (on PA11/PA12)`

Compile:

```bash
make clean
make -j4
```

Copy `out/klipper.bin` to a FAT32 SD card, rename it to `firmware.bin`, insert it into the Octopus, and power cycle the board.

After flashing, find the serial device:

```bash
ls /dev/serial/by-id/
```

Use that path in `printer.cfg`.

## 7. Create `printer.cfg`

Create `~/printer_data/config/printer.cfg` and use the liquid-handler-oriented CoreXY configuration below as a starting point:

```ini
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

[gcode_button x_max]
pin: ^PG13
press_gcode:
    M112

[gcode_button y_max]
pin: ^PG14
press_gcode:
    M112

[virtual_sdcard]
path: ~/printer_data/gcodes

[display_status]
[pause_resume]

[gcode_macro ASPIRATE_WELL]
gcode:
    {% set x = params.X|float %}
    {% set y = params.Y|float %}
    {% set vol = params.VOL|float %}
    {% set safe_z = params.SAFE_Z|default(20)|float %}
    {% set asp_z = params.ASP_Z|default(2)|float %}
    G1 X{x} Y{y} Z{safe_z} F{300*60}
    G1 Z{asp_z} F{20*60}
    G1 E-{vol * 0.1} F{5*60}
    G1 Z{safe_z} F{100*60}
    M400

[gcode_macro DISPENSE_WELL]
gcode:
    {% set x = params.X|float %}
    {% set y = params.Y|float %}
    {% set vol = params.VOL|float %}
    {% set safe_z = params.SAFE_Z|default(20)|float %}
    {% set disp_z = params.DISP_Z|default(5)|float %}
    G1 X{x} Y{y} Z{safe_z} F{300*60}
    G1 Z{disp_z} F{20*60}
    G1 E{vol * 0.1} F{5*60}
    G1 Z{safe_z} F{100*60}
    M400

[gcode_macro PROBE_LIQUID]
gcode:
    {% set x = params.X|float %}
    {% set y = params.Y|float %}
    {% set search_z = params.SEARCH_Z|default(20)|float %}
    G1 X{x} Y{y} Z{search_z} F{200*60}
    PROBE
    M400
```

Adjust motor currents, axis limits, lead screw pitch, and syringe calibration for the actual machine.

## 8. Configure Moonraker

Update `~/printer_data/config/moonraker.conf`:

```ini
[server]
host: 0.0.0.0
port: 7125
klippy_uds_address: ~/printer_data/comms/klippy.sock

[authorization]
trusted_clients:
    192.168.10.0/24
cors_domains:
    http://192.168.10.1
    http://192.168.10.2

[file_manager]
enable_object_processing: False

[octoprint_compat]

[history]
```

Restart Moonraker:

```bash
sudo systemctl restart moonraker
```

## 9. Verification

Basic bring-up checks:

1. Run `journalctl -u klipper -f` and watch for startup errors.
2. Open Mainsail and confirm the printer becomes `Ready`.
3. Run `G28 X Y` to test CoreXY homing.
4. Run `SET_KINEMATIC_POSITION X=0 Y=0 Z=0` and `G1 X10 F600` to verify motion.
5. Confirm direct Ethernet latency and control behavior before tuning further.

## Expected latency

Approximate end-to-end command latency from the source document:

- Baseline Klipper over HTTP: about `350 ms`
- WebSocket only: about `250 ms`
- WebSocket plus `toolhead.py` patch: about `40 ms`
- Plus CPU isolation: about `15-20 ms` median

## Notes

- This setup intentionally trades some motion buffering for responsiveness.
- Those timing changes are appropriate for a slow, discrete liquid handler, not a typical high-speed 3D printer.
- If the machine stutters during motion, relax the buffer values slightly.
