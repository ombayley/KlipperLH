# Moonraker Configuration

> This section details the configuration of Moonraker to accept API traffic from the direct-Ethernet control network.

Moonraker is the API layer that sits between Klipper and external clients such as:

- Mainsail in the browser
- Python control software
- any custom WebSocket or HTTP integration used by the liquid handler

For this project, Moonraker needs to trust the direct-Ethernet subnet and listen on the Pi's network interface.

---

## Prerequisite

- [Klipper Configuration](05-klipper-config.md) is complete
- Pi is reachable at `192.168.10.2`
- Controller PC is on the same direct-Ethernet subnet

You will be editing:

```text
~/printer_data/config/moonraker.conf
```

---

## Step 1 - Edit `moonraker.conf`

Open the file:

```bash
nano ~/printer_data/config/moonraker.conf
```

Use the following configuration as a starting point:

```ini
[server]
host: 0.0.0.0
port: 7125
klippy_uds_address: ~/printer_data/comms/klippy.sock

[authorization]
trusted_clients:
    192.168.10.0/24
cors_domains:
    http://192.168.10.1
    http://192.168.10.2

[file_manager]
enable_object_processing: False

[octoprint_compat]

[history]
```

What each part does:

- `host: 0.0.0.0` allows Moonraker to listen on the Pi's network interface
- `trusted_clients` allows requests from the direct-Ethernet subnet
- `cors_domains` allows browser access from the controller PC and the Pi itself

> If you changed the subnet from `192.168.10.0/24`, update these values to match your actual network.

---

## Step 2 - Restart Moonraker

Apply the configuration:

```bash
sudo systemctl restart moonraker
```

If you are using Mainsail in the browser, refresh the page afterward.

---

## Step 3 - Verify API Access

Check the service status:

```bash
sudo systemctl status moonraker
```

Then confirm the web interface is still reachable from the controller PC:

```text
http://192.168.10.2
```

At this point:

- Mainsail should load
- Moonraker should be running
- browser-based and software-based control on the direct link should now be possible

If Moonraker fails to start, inspect the service log:

```bash
journalctl -u moonraker -f
```

---

## Next Step

If you want the cleanest possible baseline before tuning, go straight to [Testing and Bring-Up](08-testing.md).

If you want to apply the optional low-latency changes first, continue to [Latency Improvements](07-latency-improvements.md).

---

## Navigation

- Previous: [Klipper Configuration](05-klipper-config.md)
- Index: [Klipper Setup Guide](../index.md)
- Next: [Latency Improvements](07-latency-improvements.md)
