
# Raspberry Pi OS Install

---

## Prerequisites
 - [**Raspberry Pi Imager**](https://www.raspberrypi.com/software/) must be installed on the local PC to flash the SD card for the Raspberry Pi
 - Ethernet Cable (*+ USB Adaptor if PC has no available Ethernet socket*)
 - Micro SD card (*+ Adaptor if PC has no available card slot*)

---

## Step 1 - Device
Select `Raspberry Pi 5`(or the pi to be used if different) from the `Device` list and select next

<img src="docs/imgs/rp_os_setup/rp_device_select.png" alt="Pi Device" height="200">

---

## Step 2 - OS
Select `Raspberry Pi OS Lite (64-bit)` from the `OS` list. If this option is not found it may be  under the `RaspberryPi OS (other)` section.
> Pi OS Lite operates with no desktop environment which keeps background CPU load low.

<img src="docs/imgs/rp_os_setup/rp_os_select_2.png" alt="Pi Device" height="200">

---

### Step 3 - Flash
Select the drive to flash

<img src="docs/imgs/rp_os_setup/rp_storage_select.png" alt="Pi Device" height="200">

---

## Step 4 - Naming
Under customisation set the hostname: `rapberry-pi` · In the *User* pane set username: `lh` and assign a password
> A password **must** be made otherwise the ssh connection later can cause issues

<img src="docs/imgs/rp_os_setup/rp_hostname.png" alt="Pi Device" height="200">

<img src="docs/imgs/rp_os_setup/rp_user.png" alt="Pi Device" height="200">

---

## Step 5 - Connectivity
**Leave WiFi unconfigured** (the device will be connected via Ethernet later) and select next.
Under Remote Access enable SSH [**IMPORTANT**] to allow connetion to the device

> No WiFi (i.e. unconfigured) removes a source of background networking interrupts that improves reliable low-latency.

<img src="docs/imgs/rp_os_setup/rp_wifi.png" alt="Pi Device" height="200">

<img src="docs/imgs/rp_os_setup/rp_ssh.png" alt="Pi Device" height="200">

---

### Step 6 - Completion
Finish the setup by completing the flashing of the SD card and then insert the newly flashed SD card into the sd card slot of the pi.
