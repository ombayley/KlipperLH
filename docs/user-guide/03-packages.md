# Install Packages

> This section details how to install the required packages on the Raspberry Pi.

This chapter installs the software stack that the rest of the guide depends on:

- `git`, so the Pi can clone repositories
- KIAUH, which is the easiest way to install and manage Klipper components
- Klipper itself
- Moonraker, the API layer
- Mainsail, the browser-based UI used for setup and manual control

---

## Prerequisites

- Pi is reachable over SSH using the network setup from [Raspberry Pi Networking](02-networking.md)
- Internet access available via the controller PC's internet sharing

If package downloads fail here, go back to the networking chapter before continuing.

---

## Step 1 - Update the Package Index

SSH into the Pi (via Terminal/PowerShell) and refresh the package lists:

```bash
sudo apt update
sudo apt upgrade -y
```

---

## Step 2 - Install Git

Install `git`, which is required to clone KIAUH:

```bash
sudo apt install git -y
```

You can verify the installation with:

```bash
git --version
```

---

## Step 3 - Clone KIAUH

Clone the KIAUH installer to the Pi user's home directory:

```bash
cd ~
git clone https://github.com/dw-0/kiauh.git
```

After this, you should have a directory at `~/kiauh`.

---

## Step 4 - Launch KIAUH

Start the KIAUH menu:

```bash
./kiauh/kiauh.sh
```

KIAUH provides a guided terminal interface for installing and managing the standard Klipper components.

---

## Step 5 - Install Klipper, Moonraker, and Mainsail

Inside the KIAUH menu:

1. choose **[1] Install**
2. install **Klipper**
3. install **Moonraker**
4. install **Mainsail**

Recommended Klipper options:

- Python version: **Python 3**
- Number of instances: **1**

Install in that order so the firmware, API layer, and browser UI are all available before you continue.

---

## Step 6 - Verify the Installation

When KIAUH finishes, check that Mainsail is reachable from the controller PC by searching for `http://192.168.10.2` 
in a web browser

What to expect:

- Mainsail should load in the browser
- it is normal to see a configuration error at this stage
- that error is expected because `printer.cfg` has not been created yet

If Mainsail does not load:

- confirm the Pi is still reachable at `192.168.10.2`
- verify Moonraker and Mainsail were both installed in KIAUH
- try refreshing the page after a minute in case services are still starting

---

## Optional Checks

If you want to confirm the services directly on the Pi:

```bash
sudo systemctl status klipper
sudo systemctl status moonraker
```

The exact status will change as configuration files are added, but the services should at least exist.

---

## Next Step

Continue to [Klipper Firmware Flashing](04-klipper-flash.md).

---

## Navigation

- Previous: [Raspberry Pi Networking](02-networking.md)
- Index: [Klipper Setup Guide](../index.md)
- Next: [Klipper Firmware Flashing](04-klipper-flash.md)
