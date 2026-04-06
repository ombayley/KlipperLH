
## Phase 8 — Moonraker Configuration

```ini
# ~/printer_data/config/moonraker.conf

[server]
host: 0.0.0.0
port: 7125
klippy_uds_address: ~/printer_data/comms/klippy.sock

[authorization]
trusted_clients:
    192.168.10.0/24         # allow your whole direct-ethernet subnet
cors_domains:
    http://192.168.10.1
    http://192.168.10.2

[file_manager]
enable_object_processing: False

[octoprint_compat]

[history]
```

```bash
sudo systemctl restart moonraker
```

---