# Klipper Firmware Flashing

> By the end of this section, the Octopus board will be running a Klipper firmware image that matches your MCU and communication method.

---

## At a Glance

| Item | Value |
| --- | --- |
| Goal | Build and flash the Octopus-side Klipper firmware |
| Estimated time | 20 to 40 minutes depending on flashing method |
| You finish with | A visible `/dev/serial/by-id/` device for the flashed Octopus |

---

## What This Section Does

Klipper runs in two places:

- the Raspberry Pi runs the high-level Klipper host software
- the Octopus runs the Klipper MCU firmware

This chapter covers the Octopus side. You will build a firmware image on the Pi, then flash it to the board either through **USB DFU mode** or by copying `firmware.bin` to a microSD card.

---

## Before You Start

Make sure:

- [Install Packages](03-packages.md) is complete
- the Pi can be reached over SSH
- the Octopus is connected to the Pi if you plan to use USB flashing
- the Octopus is powered correctly

It is also important to know which MCU your Octopus board actually has. Common variants include:

| MCU | Bootloader Offset | Clock Reference |
| --- | --- | --- |
| `STM32F446` | `32KiB bootloader` | `12 MHz crystal` |
| `STM32F429` | `32KiB bootloader` | `8 MHz crystal` |
| `STM32H723` | `128KiB bootloader` | `25 MHz crystal` |

> Check the board label, documentation, or bill of materials before compiling. Selecting the wrong MCU settings will produce a firmware image that does not boot correctly.

---

## Step 1 - Build the Firmware Image

SSH into the Pi and prepare the Klipper build directory:

```bash
sudo apt install make -y
cd ~/klipper
make clean
make menuconfig
```

In `make menuconfig`, select the settings that match your board:

- enable **extra low-level configuration options**
- set **Micro-controller Architecture** to `STMicroelectronics STM32`
- set **Processor model** to the correct MCU for your board
- set **Bootloader offset** to match that MCU
- set **Clock Reference** to match that MCU
- set **Communication interface** to `USB (on PA11/PA12)` if you are using USB between the Pi and Octopus

Reference screenshots:

**STM32F446**

<img src="../imgs/klipper_install/klipper_menuconfig_STM32_F446.png" alt="Klipper menuconfig for STM32F446" width="700">

**STM32F429**

<img src="../imgs/klipper_install/klipper_menuconfig_STM32_F429.png" alt="Klipper menuconfig for STM32F429" width="700">

**STM32H723**

<img src="../imgs/klipper_install/klipper_menuconfig_STM32_H723.png" alt="Klipper menuconfig for STM32H723" width="700">

When the configuration is correct:

1. press `Q`
2. choose **Yes** when asked to save
3. build the firmware

```bash
make -j4
```

When the build completes, the generated firmware file will be:

```text
~/klipper/out/klipper.bin
```

---

## Step 2 - Choose a Flashing Method

There are two standard ways to install the firmware on the Octopus:

- **USB DFU mode**
  Best when the board is already connected to the Pi over USB and you are comfortable setting the boot jumpers.
- **microSD card**
  Usually the simplest and least error-prone method if you have a spare card available.

Use whichever route is more convenient for your build.

---

## Option A - Flash Over USB Using DFU Mode

### When to Use This Method

Use USB DFU flashing if:

- the Pi and Octopus are connected by USB
- you are comfortable moving the `BOOT0` jumper
- you want to flash directly without copying files to a card

### Procedure

1. Power off the Octopus
2. Install the `BOOT0` jumper
3. Install a jumper between `GND` and `PB2` to pull `BOOT1` low
4. Connect the Octopus to the Pi over USB
5. Power on the Octopus
6. Press the reset button next to the USB connector
7. On the Pi, go to the Klipper directory:

```bash
cd ~/klipper
```

8. Confirm the board appears in DFU mode:

```bash
lsusb
```

Look for a device similar to `STM Device in DFU Mode`.

9. Flash the firmware using the detected device ID:

```bash
make flash FLASH_DEVICE=1234:5678
```

Replace `1234:5678` with the USB ID reported by `lsusb`.

10. Power off the Octopus
11. Remove the `BOOT0` jumper
12. Power on the Octopus again
13. Check that the flashed board now appears as a Klipper serial device:

```bash
ls /dev/serial/by-id/
```

Expected output will look similar to:

```text
usb-Klipper_stm32f446xx_XXXXXXXX-if00
```

### Why the BOOT1 Jumper Matters

On this board family, entering the correct STM32 boot mode depends on both `BOOT0` and `BOOT1`.

- `BOOT0` must be high
- `BOOT1` must be low

On the Octopus, the STM32 `BOOT1` line is associated with `PB2`, which can otherwise float. Pulling `PB2` to ground ensures the MCU enters the correct boot mode for DFU flashing instead of landing in an invalid state.

Reference pinout:

<img src="../imgs/klipper_install/octopus_pinout.png" alt="Octopus pinout showing BOOT-related pins" width="700">

---

## Option B - Flash Using a microSD Card

### When to Use This Method

Use the SD-card method if:

- you have a spare microSD card available
- you want a simple manual flashing workflow
- USB DFU mode is inconvenient or unavailable

### Procedure

1. On the Pi, create the exact filename expected by the bootloader:

```bash
cd ~/klipper
cp out/klipper.bin out/firmware.bin
```

2. Copy `~/klipper/out/firmware.bin` from the Pi to your controller PC
3. Format the microSD card as **FAT32**
4. Copy `firmware.bin` to the root of that card
5. Power off the Octopus
6. Insert the microSD card into the Octopus
7. Power the Octopus back on
8. Wait a few seconds for the bootloader to flash the image
9. Reconnect to the Pi and check for the Klipper serial device:

```bash
ls /dev/serial/by-id/
```

Again, you are looking for something similar to:

```text
usb-Klipper_stm32f446xx_XXXXXXXX-if00
```

> The file must be named `firmware.bin`. If the name is wrong, the bootloader will ignore it.

---

## Check Your Work

This section is complete when:

- the firmware build finished without errors
- the Octopus appears under `/dev/serial/by-id/`
- you know the exact serial path for the board

Keep that serial path. You will need it in `printer.cfg` in the next chapter.

---

## Troubleshooting

If the board does not appear after flashing:

- confirm you built the firmware for the correct MCU
- confirm the board has proper main power, not just USB power
- confirm the communication interface chosen in `menuconfig` matches your intended wiring
- if using DFU, make sure `BOOT0` was removed after flashing

If the board powers up but drivers or peripherals do not respond correctly:

- verify the Octopus is powered from the correct 12 to 24 V supply
- verify the board is not being tested from USB power alone

---

## Next Step

Continue to [Klipper Configuration](05-klipper-config.md).

---

## Navigation

- Previous: [Install Packages](03-packages.md)
- Index: [Klipper Setup Guide](../index.md)
- Next: [Klipper Configuration](05-klipper-config.md)
