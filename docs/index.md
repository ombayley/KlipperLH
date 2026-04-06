# <img src="imgs/klipper_logo.png" alt="Klipper logo" height="28"> Klipper Setup Guide

This guide documents the full low-level setup for the Klipper-based motion stack used by the liquid handler. It is written for someone starting from an empty Raspberry Pi SD card and an unflashed Octopus board.

The final system uses:

| Component              | Selected Platform                                      |
|------------------------|--------------------------------------------------------|
| Single-board computer  | Raspberry Pi 5                                         |
| Pi operating system    | Raspberry Pi OS Lite (64-bit)                          |
| Motion controller      | BigTreeTech Octopus                                    |
| Firmware               | Klipper                                                |
| API / remote control   | Moonraker                                              |
| Browser interface      | Mainsail                                               |
| Final network topology | Direct Ethernet between controller PC and Raspberry Pi |

---

## Read This First

This guide assumes the following defaults unless you intentionally choose different values:

| Setting                      | Recommended Value |
|------------------------------|-------------------|
| Raspberry Pi hostname        | `raspberry-pi`    |
| Raspberry Pi username        | `lh`              |
| Raspberry Pi final static IP | `192.168.10.2`    |
| Controller PC Ethernet IP    | `192.168.10.1`    |

If you use different names or addresses, keep them consistent throughout the guide.

---

## Why This Stack Is Used

Klipper and Moonraker are mature, well-documented tools originally popularised in high-performance open-source 3D printers such as [Voron](https://vorondesign.com/), [RatRig](https://ratrig.com/), and [VZBot](https://vzbot.org/). That matters for this project because:

- the motion system already supports complex kinematics such as CoreXY
- the software ecosystem is large and actively documented
- the configuration model is flexible enough to adapt printer-oriented firmware to liquid-handling hardware

Liquid handling does, however, have different response requirements from 3D printing. Instead of long buffered toolpaths, it relies on shorter point-to-point moves and benefits from lower command-to-motion latency. That is why this guide also includes optional latency improvements after the baseline system is working.

---

## Known Good Baseline

This guide is designed to get you to a **known working baseline** before you start customising or optimising anything.

That means:

- use the documented hostnames, IPs, and install order unless you have a reason not to
- confirm each chapter is working before moving to the next one
- leave the optional latency tuning until the standard setup is already stable

If you later want to adapt the machine, do it from a working baseline rather than during initial bring-up.

---

## Recommended Build Sequence

Follow the chapters in this order:

| Step  | Chapter                                                       | What You Complete                                                                    |
|-------|---------------------------------------------------------------|--------------------------------------------------------------------------------------|
| 1     | [Raspberry Pi OS Install](user-guide/01-pi-install.md)        | Flash the SD card and enable SSH                                                     |
| 2     | [Raspberry Pi Networking](user-guide/02-networking.md)        | Bring the Pi online, share internet temporarily, then move to static direct Ethernet |
| 3     | [Install Packages](user-guide/03-packages.md)                 | Install Git, KIAUH, Klipper, Moonraker, and Mainsail                                 |
| 4     | [Klipper Firmware Flashing](user-guide/04-klipper-flash.md)   | Build and flash firmware for the Octopus                                             |
| 5     | [Klipper Configuration](user-guide/05-klipper-config.md)      | Create `printer.cfg` for the liquid handler                                          |
| 6     | [Moonraker Configuration](user-guide/06-moonraker-config.md)  | Enable API access over the direct Ethernet link                                      |
| 7     | [Latency Improvements](user-guide/07-latency-improvements.md) | Apply optional low-latency tuning once the baseline system works                     |
| 8     | [Testing and Bring-Up](user-guide/08-testing.md)              | Verify motion, communication, and expected performance                               |

---

## Before You Start

Have the following ready:

- Raspberry Pi 5 with power supply
- microSD card for the Raspberry Pi
- BigTreeTech Octopus board
- USB cable between Pi and Octopus if using USB flashing / USB communication
- Ethernet cable between the controller PC and the Pi
- A controller PC with [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
- A way to transfer files if you plan to use the SD-card firmware flash method

It is also worth deciding one thing up front: whether you want to flash the Octopus over USB DFU mode or via microSD card. Both methods are covered later.

---

## Guide Quality Goals

Each chapter in this guide follows the same structure:

- what the section accomplishes
- what you need before you begin
- the exact commands or settings to enter
- how to verify that the step worked
- where to go next

If something does not match your hardware exactly, stop and resolve the mismatch before moving on. Most setup problems come from small inconsistencies in usernames, IP addresses, MCU variants, or wiring assumptions.

---

## Start Here

Begin with [Raspberry Pi OS Install](user-guide/01-pi-install.md).

---

### Author
**Olly Bayley** · *ollybayley1@gmail.com* · 2026
