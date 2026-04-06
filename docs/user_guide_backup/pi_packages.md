# Install Packages

To install the required klipper-related packages, linux's `apt` (Advanced Package Tool) package manager should be first be
updated and subsequently git installed via apt. With git installed we can use KIAUH to pull the rest of the Klipper 
related packages.

---

## Prerequisites
 - Internet connectivity via host sharing as described [here](pi_network.md) 

---

## Step 1 — Update apt

```bash
sudo apt update
sudo apt upgrade -y
```

---

## Step 2 — Install git

```bash
sudo apt install git -y
```

---

## Step 3 — Clone KIUAH

```bash
cd ~
git clone https://github.com/dw-0/kiauh.git
```

## Step 4 — Install Klipper, Moonraker, and Mainsail

```bash
./kiauh/kiauh.sh
```

In the KIAUH menu select **[1] Install** in this order:

1. Klipper — Python 3, 1 instance
2. Moonraker — the API layer
3. Mainsail — web UI for manual testing

> **Verify.** After KIAUH finishes, `http://192.168.10.2` should load Mainsail. A config error is expected — `printer.cfg` doesn't exist yet.






