# Raspberry Pi OS Install

> This section details how to set up and configure the headless OS that will be running on the Raspberry Pi

---

## Prerequisites
- Raspberry Pi (*ideally a 4 or 5*)
- A microSD card and a card reader (*either built-into the PC or as a USB adaptor*)
- Controller PC that will be used to prepare the card
- [Raspberry Pi Imager](https://www.raspberrypi.com/software/) installed on the controller PC

---
## Assumed Defaults

Recommended settings used throughout this guide:

| Setting  | Recommended Value               |
|----------|---------------------------------|
| Device   | `Raspberry Pi 5`                |
| OS       | `Raspberry Pi OS Lite (64-bit)` |
| Hostname | `raspberry-pi`                  |
| Username | `lh`                            |
| Wi-Fi    | unconfigured                    |
| SSH      | enabled                         |

> If you choose different values, keep a note of them as you will need to substitute them in later chapters.


This system uses **Raspberry Pi OS Lite (64-bit)** rather than the full desktop image to avoid the extra overhead 
and latency fluctuation from the unused background processes. For a permanently embedded motion controller, 
low overheads and predictable latency are much more important than native desktop and GUI elements.

---

## Step 1 - Select the Device

Open Raspberry Pi Imager and choose the target board.

1. Click **Device**
2. Select **Raspberry Pi 5**
3. Click **Next**

<img src="../imgs/rp_os_setup/rp_device_select.png" alt="Selecting Raspberry Pi 5 in Raspberry Pi Imager" width="700">

---

## Step 2 - Select the Operating System

Choose the lightweight operating system image.

1. Select **Raspberry Pi OS Lite (64-bit)**
2. If you do not see it immediately, look under **Raspberry Pi OS (other)**
3. Click **Next**

<img src="../imgs/rp_os_setup/rp_os_select_2.png" alt="Selecting Raspberry Pi OS Lite 64-bit" width="700">

> *Avoid the desktop image unless you have a specific need for it.*

---

## Step 3 - Select the Storage Device

Choose the microSD card to be flashed.

1. Insert the microSD card into the controller PC
2. Select the correct removable drive
3. Click **Next**

<img src="../imgs/rp_os_setup/rp_storage_select.png" alt="Selecting the target microSD card" width="700">

> Double-check the selected drive before writing. Raspberry Pi Imager will erase it.

---

## Step 4 - Open the Customisation Settings

Before writing the card, open the customisation settings so the Pi is ready for headless access on first boot.

1. Set hostname to `raspberry-pi`
2. Click **Next**
3. Set relevant time and keyboard in **Localisation**
4. Click **Next**
5. Set username to `lh` and add a password of your choice
6. Click **Next**

<img src="../imgs/rp_os_setup/rp_hostname.png" alt="Setting the Raspberry Pi hostname" width="700">

<img src="../imgs/rp_os_setup/rp_user.png" alt="Setting the Raspberry Pi username and password" width="700">

> **Do not leave the password blank**. SSH access is much easier to set up later if the initial user account is valid from the start.

---

## Step 5 - Leave Wi-Fi Disabled and Enable SSH

This build is designed to run over Ethernet rather than Wi-Fi, so leave wireless networking unconfigured.

In the same customisation dialog:

1. Leave all **Wi-Fi** options unset
2. Click **Next** to get to the **Remote Access** pane
3. Enable **SSH**
4. Click **Next** and optionally setup Raspberry Pi Connect.

<img src="../imgs/rp_os_setup/rp_wifi.png" alt="Leaving Wi-Fi unconfigured in Raspberry Pi Imager" width="700">

<img src="../imgs/rp_os_setup/rp_ssh.png" alt="Enabling SSH in Raspberry Pi Imager" width="700">

> **Important:** Make sure SSH is enabled as without a desktop or internet connection the only method to connect to 
> the pi is via ssh on a direct  Ethernet connection

---

## Step 6 - Write the SD Card

Finish the imaging process.

1. Click **Next**
2. Confirm the customisation settings
3. Click **Yes** to write the card
4. Wait for flashing and verification to complete

When Raspberry Pi Imager finishes:

1. remove the microSD card safely
2. insert it into the Raspberry Pi
3. power on the Pi
4. wait about 30 to 60 seconds for the first boot

---

## Next Step

Continue to [Raspberry Pi Networking](02-networking.md).

---

## Navigation

- Index: [Klipper Setup Guide](../index.md)
- Next: [Raspberry Pi Networking](02-networking.md)
