
# <img src="docs/imgs/klipper_logo.png" alt="Klipper Setup Guide" height="25"> Klipper Setup Guide

> Step-by-step guide to prepare the low-level firmware and configuration for the liquid handler

---

## Overview

The the motion control of the liquid handler is based on the well-established Klipper + Moonraker tech stack used in many 3D printers.
This control system has been a mainstay in high-performance open-source FDM printers such as the 
[Voron](https://vorondesign.com/),
[RatRig](https://ratrig.com/),
[VZbot](https://vzbot.org/)
and [more](https://github.com/klipper3d/klipper).
This means there is a huge community who can provide help on issues arising from this stack and there are many tutorials available which are well documented.

The core driver towards using this tech stack is it's inbuilt kinematics and input shaping ability that allows many
types of motion systems to be used and the motion smoothed with maximal accelerations and path selection. 

As this system is typically used for 3D printing where workflows build highly complex motion paths and can accomodate 
a greater delay between command and start of motion for motion bufferring, Liquid handlers have much simpler 
point-to-point motion path and ideally need to repond more quickly. As such this guide also includes liquid handler specific patches to 
decrease command-response latency.

| Component             | Choice                                                |
|-----------------------|-------------------------------------------------------|
| Single-board computer | Raspberry Pi 5 — Raspberry Pi OS Lite (64-bit)        |
| Motion controller     | BTT Octopus (STM32F446)                               |
| Firmware + API        | Klipper + Moonraker + Mainsail via KIAUH              |
| Network               | Direct Ethernet — static IP, no WiFi, no mDNS         |
| Key patches           | Patched `toolhead.py` look-ahead · CPU core isolation |

---


## Step Overview

1) [Pi OS Install](pi_install.md)
2) [Network Configuration](pi_network.md)
3) [Package Installation](pi_packages.md)
4) [Disable Network Sharing (Optional) ](pi_network.md#optional--disable-internet-sharing)
5) [Flash Klipper onto the Octopus](klipper_flash.md)
6) [Configure the Klipper settings](klipper_config.md)
7) [Configure the moonraker settings (the API)](moonraker_config.md)
8) [Add latency improvement fixes (Optional)](latency_improvements.md)
9) [Test the system reccieves commands and actions motors](testing.md)

---

### Author  
**Olly Bayley** - *ollybayley1@gmail.com* (2026)