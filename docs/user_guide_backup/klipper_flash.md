# Klipper Firmware Flashing

Once Klipper is installed on the pi, the firmware for the control board must be flashed.  

---

## Prerequisites
Klipper must be installed onto the Raspberry Pi
It is desirable, though not strictly necessary to have a small sdcard available
Even if you intend to power your Pi with the Octopus, during this flashing process, you will find it far more convenient to power your Pi from some other source, such as a regular USB power supply
Voron Design recommends using USB to control the Octopus, which simply requires connecting a USB-A to USB-C cable between the Octopus and Pi. If you prefer a UART connection, please consult the BigTreeTech documentation for the necessary configuration adjustments


---

## Step 1 — Build Firmware Image 
SSH into the Raspberry Pi and Run:

```bash
sudo apt install make
cd ~/klipper
make clean
make menuconfig

```

In the menu structure there are a number of items to be selected.

- Select “Enable extra low-level configuration options”
- Set the micro-controller architecture is set to `STMicroelectronics STM32`
- Set the Processor model to `STM32F446`,`STM32F429` or `STM32H723` (Depends on the MCU of your motherboard)
- Set the Bootloader offset to `32KiB bootloader` (for `STM32F446`, `STM32F429`) or `128KiB bootloader` (for `STM32H723`)
- Set the Clock Reference to `12 MHz crystal` (for `STM32F446`), `8 MHz crystal` (for `STM32F429`), `25MHz crystal` (for `STM32H723`)
- Set the Communication interface to `USB (on PA11/PA12)` (note: see [BigTreeTech documentation](https://github.com/bigtreetech/BIGTREETECH-OCTOPUS-V1.0/tree/master/Octopus%20works%20on%20Voron%20v2.4/Firmware/Klipper) if you intend to use UART rather than USB)

<img src="docs/imgs/klipper_install/klipper_menuconfig_STM32_F446.png" alt="Klipper settings" height="200">


<img src="docs/imgs/klipper_install/klipper_menuconfig_STM32_F429.png" alt="Klipper settings" height="200">


<img src="docs/imgs/klipper_install/klipper_menuconfig_STM32_H723.png" alt="Klipper settings" height="200">

Once the configuration is selected, press q to exit, and “Yes” when asked to save the configuration.
Run the command make
The make command, when completed, creates a firmware file klipper.bin which is stored in the folder /home/pi/klipper/out.

### Settings (Short)

| Setting                       | Value                    |
|-------------------------------|--------------------------|
| Micro-controller Architecture | STMicroelectronics STM32 |
| Processor model               | STM32F446                |
| Bootloader offset             | 32KiB bootloader         |
| Clock Reference               | 12 MHz crystal           |
| Communication interface       | USB (on PA11/PA12)       |


---

## Step 2 - Flash Firmware Image to Octopus 

There are multiple options for getting this firmware file installed onto your Octopus.
The most common routes are either [via USB](#dfu-firmware-install-via-usb) or [via SD Card](#sd-card-firmware-install)


### DFU Firmware Install via USB
> - Requires a USB connection
> - Requires the installation of an extra jumper on the Octopus
> - Does NOT require a sd card

1) Power off Octopus
2) Install the BOOT0 jumper (Located near the AUX headers)
3) Install a jumper between GND and PB2 for [BOOT1](#boot1) floating pin fix
4) Connect Octopus & Pi via USB-C 
5) Power on Octopus 
6) Press the reset button next to the USB connector 
7) From your ssh session, run `cd ~/klipper` to make sure you are in the correct directory 
8) Run `lsusb` in the terminal. and find the ID of the dfu device. The device is typically named `STM Device in DFU mode`. 
9) Run make `flash FLASH_DEVICE=1234:5678`, replacing `1234:5678` with the ID from the previous step. Note that the ID is in hexadecimal form; it only contains the numbers 0-9 and letters A-F. 
10) Power off the Octopus 
11) Remove the jumper from `BOOT0`
12) Power on the Octopus 
13) You can confirm that the flash was successful by running `ls /dev/serial/by-id`. If the flash was successful, this should now show a klipper device, similar to:
```bash
lh@rapberry-pi:~/klipper $ ls /dev/serial/by-id
usb-Klipper_stm32f446xx_...
```


#### BOOT1
To enter different boot modes STM32 chips require both the BOOT0 and BOOT1 pins to be set. [REF](https://deepbluembedded.com/stm32-boot-modes-stm32-boot0-boot1-pins/)
For DFU mode (the mode required to access system memory and flash the klipper image) `BOOT0` must be set `HIGH` and `BOOT1` set `LOW`.
If both `BOOT0` an `BOOT1` are `HIGH`, then it will launch into the empty embedded SRAM, making the board appear dead. 
Unfortunately the BOOT1 pin of the STM chip in the Octopus is wired to the PB2 pin in the EXP2 junction which leaves the pin floating.
This pin must be connected to GND to pull the `BOOT1` pin `LOW` (Shown in Pin diagram below).

<img src="docs/imgs/klipper_install/octopus_pinout.png" alt="Octopus Pinout" height="200">


### SD Card Firmware Install
> - Requires a microSD card
> - Works regardless of USB vs UART

1) Run via SSH to rename the firmware file to firmware.bin: 
```bash
cd ~/klipper
mv out/klipper.bin out/firmware.bi
```

> Important: If the file is not renamed, the firmware will not be updated properly. The bootloader looks for a file named `firmware.bin`.
 
2) Use a tool such as cyberduck or winscp to copy the firmware.bin file off your Pi, onto your computer.
3) Ensure that your sdcard is formatted FAT32 (NOT EXFAT!)
4) Copy firmware.bin onto the microSD card 
5) Power off the Octopus 
6) Insert the microSD card 
7) Power on the Octopus 
8) After a few seconds, the Octopus should be flashed
9) You can confirm that the flash was successful by running `ls /dev/serial/by-id`. If the flash was successful, this should now show a klipper device, similar to:
```bash
lh@rapberry-pi:~/klipper $ ls /dev/serial/by-id
usb-Klipper_stm32f446xx_...
```

---

## Note

> Important: If the Octopus is not powered with 12-24V, Klipper will be unable to communicate with the TMC drivers via UART and the Octopus will automatically shut down.