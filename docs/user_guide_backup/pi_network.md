# Raspberry Pi OS Post-Install Configure (No Internet Setup)

Since the liquid handler is designed to run on a **direct Ethernet connection (no router, no WiFi)**, the Raspberry Pi will not have internet access by default. 
To install required packages onto the pi via linux's `apt` (Advanced Package Tool) package manager, we temporarily **share the controller PC’s internet connection over Ethernet**.

---

## Step 1 — Connect Hardware

1. Insert the flashed SD card into the Raspberry Pi  
2. Connect:
   - Ethernet cable between **Pi ↔ PC**
   - Power to the Pi
3. Wait ~30–60 seconds for boot

---

## Step 2 — Enable Internet Sharing on Controller PC

You need to bridge or share your PC’s internet (WiFi or LAN) to the Ethernet port connected to the Pi.

### On Windows

1. Go to:  
   `Control Panel → Network and Sharing Center → Change adapter settings`

2. Right-click your **internet-connected adapter** (WiFi or LAN) → **Properties**

3. Open the **Sharing** tab:
   - Enable: *“Allow other network users to connect…”*
   - Select your **Ethernet adapter**

4. Click OK

> Windows will typically assign the Ethernet adapter: `192.168.137.1`


### On Linux (NetworkManager)

```bash
nm-connection-editor
```

- Select your Ethernet connection
- Set:
  - IPv4 Method → **Shared to other computers**

Or via CLI:

```bash
nmcli connection modify "Wired connection 1" ipv4.method shared
nmcli connection up "Wired connection 1"
```


### On macOS

1. Go to:  
   `System Settings → General → Sharing`

2. Enable **Internet Sharing**
3. Share from: **WiFi**
4. To: **Ethernet**

---

## Step 3 — SSH into the Pi

Once sharing is enabled, the Pi should receive an IP automatically.

Try:

```bash
ssh lh@raspberry-pi.local
```

If mDNS fails, find the IP:

- Windows:
  ```bash
  arp -a
  ```
- Linux/macOS:
  ```bash
  ip neigh
  ```

Then:

```bash
ssh lh@<PI_IP>
```

---

## Step 4 — Configure Static Direct Ethernet

Assign a fixed IP so your PC can always reach the Pi without mDNS resolution overhead.

```bash
# /etc/dhcpcd.conf — add at the bottom
interface eth0
static ip_address=192.168.10.2/24
static routers=192.168.10.1
```

Set Ethernet adapter manually:

| Field       | Value                   |
|-------------|-------------------------|
| IP address  | 192.168.10.1            |
| Subnet mask | 255.255.255.0           |
| Gateway     | 192.168.10.2 (or blank) |

```bash
ping 192.168.10.2       # should see <1ms RTT
ssh lh@192.168.10.2     # confirm SSH works on static IP
```

---

## OPTIONAL — Disable Internet Sharing

Once packages are installed there is no longer a need for an internet connection as the final system runs fully offline.

- **Turn OFF internet sharing on your PC**
- We will switch to **static direct Ethernet** in the next phase

> This ensures:
> - No DHCP interference  
> - No background broadcast traffic  
> - Deterministic low-latency networking
