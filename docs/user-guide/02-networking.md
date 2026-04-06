# Raspberry Pi Networking

> By the end of this section, the Raspberry Pi will be reachable over SSH and configured for the final direct-Ethernet static IP setup used by the liquid handler.

---

## At a Glance

| Item | Value |
| --- | --- |
| Goal | Bring the Pi online, install a temporary shared-internet path, then move to static Ethernet |
| Estimated time | 15 to 25 minutes |
| You finish with | SSH access and a fixed direct-Ethernet address of `192.168.10.2` |

---

## What This Section Does

The liquid handler runs with a **direct Ethernet cable between the controller PC and the Raspberry Pi**, with no router and no Wi-Fi. That is ideal for predictable local control, but it also means the Pi does not have internet access by default.

To install packages in the next chapter, this section uses a temporary two-stage approach:

1. share the controller PC's internet connection over Ethernet so the Pi can install packages
2. switch the link to a static direct-Ethernet configuration for permanent use

---

## Before You Start

Make sure:

- the Raspberry Pi has already been flashed as described in [Raspberry Pi OS Install](01-pi-install.md)
- the Pi is powered on
- the Pi is connected to the controller PC by Ethernet
- you know the Pi username you configured earlier

This guide assumes:

| Device | Address / Name |
| --- | --- |
| Raspberry Pi hostname | `raspberry-pi.local` |
| Raspberry Pi final static IP | `192.168.10.2` |
| Controller PC Ethernet IP | `192.168.10.1` |

---

## Step 1 - Connect the Hardware

Confirm the physical connections before changing any network settings.

1. Insert the prepared microSD card into the Raspberry Pi if it is not already installed
2. Connect an Ethernet cable directly between the Pi and the controller PC
3. Power on the Pi
4. Wait roughly 30 to 60 seconds for it to boot

At this point the Pi is physically ready, but it still needs network configuration to reach package servers.

---

## Step 2 - Temporarily Share Internet from the Controller PC

Enable internet sharing on the controller PC so the Pi can install packages during setup.

### Windows

1. Open `Control Panel > Network and Sharing Center > Change adapter settings`
2. Right-click the adapter that already has internet access
3. Select **Properties**
4. Open the **Sharing** tab
5. Enable **Allow other network users to connect through this computer's Internet connection**
6. Select the Ethernet adapter connected to the Raspberry Pi
7. Click **OK**

Windows commonly assigns the shared Ethernet adapter the address `192.168.137.1`.

### Linux with NetworkManager

Open the connection editor:

```bash
nm-connection-editor
```

Then set the Ethernet connection to **Shared to other computers**.

Or use the command line:

```bash
nmcli connection modify "Wired connection 1" ipv4.method shared
nmcli connection up "Wired connection 1"
```

### macOS

1. Open `System Settings > General > Sharing`
2. Enable **Internet Sharing**
3. Share from the internet-connected interface, usually **Wi-Fi**
4. Share to **Ethernet**

> Temporary internet sharing is only needed long enough to install packages. Once setup is complete, the final system should run offline on the dedicated Ethernet link.

---

## Step 3 - SSH into the Raspberry Pi

With internet sharing enabled, the Pi should obtain an address automatically.

Try connecting with mDNS first:

```bash
ssh lh@raspberry-pi.local
```

If you chose a different username or hostname earlier, substitute them here.

If `.local` name resolution does not work, find the Pi's current IP address from the controller PC:

### Windows

```bash
arp -a
```

### Linux or macOS

```bash
ip neigh
```

Then connect directly:

```bash
ssh lh@<PI_IP>
```

If SSH asks you to trust the host key, accept it and continue.

---

## Step 4 - Configure the Raspberry Pi Static Ethernet Address

Once you are logged in, set the Pi's Ethernet interface to the permanent static address used by the rest of the guide.

Open the DHCP client configuration:

```bash
sudo nano /etc/dhcpcd.conf
```

Add the following lines at the end of the file:

```conf
interface eth0
static ip_address=192.168.10.2/24
static routers=192.168.10.1
```

Save the file and exit the editor.

> If you use a different subnet, update both the Pi and controller PC values consistently.

---

## Step 5 - Configure the Controller PC Ethernet Adapter

Set the controller PC Ethernet adapter to a matching static address.

Use:

| Field | Value |
| --- | --- |
| IP address | `192.168.10.1` |
| Subnet mask | `255.255.255.0` |
| Gateway | `192.168.10.2` or leave blank |

The exact UI differs by operating system, but the goal is always the same: make the PC and Pi peers on the same private subnet.

---

## Step 6 - Reconnect and Verify the Final Static Link

Reconnect to the Pi using the final address:

```bash
ping 192.168.10.2
ssh lh@192.168.10.2
```

What you want to see:

- the Pi responds to `ping`
- SSH connects successfully using `192.168.10.2`
- round-trip time is very low, typically less than 1 ms on a direct cable

---

## Optional - Disable Internet Sharing Again

Once package installation is complete in the next chapter, you can disable internet sharing on the controller PC and leave the system as a fully offline point-to-point network.

Reasons to disable sharing afterward:

- avoids DHCP interference
- reduces broadcast and background network traffic
- keeps the final control network predictable

If you disable sharing before package installation, the Pi will lose internet access and `apt` will fail.

---

## Troubleshooting

If SSH does not connect:

- confirm the Pi finished booting
- re-check the username you configured during imaging
- confirm the Ethernet link lights are active
- verify the controller PC is actually sharing internet in the temporary phase

If the static address does not work after editing `dhcpcd.conf`:

- re-open the file and check for typing mistakes
- make sure the controller PC Ethernet adapter was also updated
- disconnect and reconnect the Ethernet adapter if needed

---

## Next Step

Continue to [Install Packages](03-packages.md).

---

## Navigation

- Previous: [Raspberry Pi OS Install](01-pi-install.md)
- Index: [Klipper Setup Guide](../index.md)
- Next: [Install Packages](03-packages.md)
