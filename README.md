# KlipperLH

`KlipperLH` is an async Python control layer for a Klipper-based liquid handler. It provides:

- A reconnecting Moonraker WebSocket client
- Motion primitives with short-window move coalescing
- YAML-driven deck and labware resolution
- Pipette volume helpers
- Liquid-level probing hooks
- An async session context manager for connect/home/park/disconnect lifecycle handling

The repository also includes the low-latency Klipper setup notes for the Raspberry Pi and BTT Octopus hardware stack used by this project.

## Project Layout

```text
lh/
  protocols.py
  exceptions.py
  config.py
  client.py
  motion.py
  deck.py
  tools.py
  pipette.py
  level_detect.py
  session.py
tests/
examples/
config/default.yaml
```

## Requirements

- Python 3.11+
- `websockets>=12`
- `pydantic>=2`
- `pyyaml`

Development tools:

- `pytest`
- `pytest-asyncio`
- `ruff`
- `mypy`

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Configuration

The default configuration lives in `config/default.yaml`. It contains:

- Moonraker host and reconnect settings
- Motion defaults including coalescing window and safe Z
- Deck slot origins and labware layout definitions
- Tool parking coordinates and offsets
- Pipette axis and volume calibration

Load it with:

```python
from pathlib import Path

from lh.config import load_config

config = load_config(Path("src/device_config/default.yaml"))
```

## Example

`examples/basic_session.py` shows a complete startup flow:

```python
from pathlib import Path

from lh.client import MoonrakerClient
from lh.config import load_config
from lh.deck import Deck
from lh.motion import MotionController
from lh.pipette import Pipette
from lh.session import LiquidHandlerSession
from lh import ToolHead

config = load_config(Path("src/device_config/default.yaml"))
client = MoonrakerClient(config.moonraker)
motion = MotionController(client=client, config=config.motion)
deck = Deck(config.deck)
tool = ToolHead(config.tool)
pipette = Pipette(mover=motion, config=config.pipette)
```

Key runtime behaviour:

- JSON-RPC request ids are monotonic integers
- Pending RPC requests are tracked in `dict[int, asyncio.Future]`
- Disconnects trigger exponential-backoff reconnect attempts
- Object subscriptions are replayed after reconnect
- `send_fire_forget()` schedules writes with `asyncio.create_task()`
- `wait_ready()` blocks until Moonraker reports `klippy_state == "ready"`
- Motion commands arriving within `coalesce_window_ms` are combined into one script call

## Testing

Run the test suite with:

```bash
pytest
```

The test coverage targets:

- Move coalescing
- Probe-result parsing
- Deck resolution
- Session lifecycle handling

## Klipper System Setup

This project assumes a low-latency Klipper deployment with:

- Raspberry Pi 5
- BTT Octopus
- Klipper, Moonraker, and Mainsail
- Direct Ethernet between the workstation and the Pi
- Reduced Klipper look-ahead buffering

### 1. Flash Raspberry Pi OS

Use Raspberry Pi Imager and select:

- Device: Raspberry Pi 5
- OS: Raspberry Pi OS Lite (64-bit)
- Hostname: `liquidhandler`
- Username: `pi`
- SSH enabled
- Wi-Fi left unconfigured

Initial update:

```bash
ssh pi@liquidhandler.local
sudo apt update && sudo apt upgrade -y
sudo apt install git -y
```

### 2. Configure direct Ethernet

Add this to `/etc/dhcpcd.conf` on the Pi:

```conf
interface eth0
static ip_address=192.168.10.2/24
static routers=192.168.10.1
```

Set the workstation Ethernet adapter to:

- IP address: `192.168.10.1`
- Subnet mask: `255.255.255.0`
- Gateway: `192.168.10.2` or blank

Verify:

```bash
ping 192.168.10.2
ssh pi@192.168.10.2
```

### 3. Isolate a CPU core for Klippy

Append this to the existing single line in `/boot/firmware/cmdline.txt`:

```text
isolcpus=3 rcu_nocbs=3 nohz_full=3
```

Then create a systemd override:

```ini
[Service]
Nice=-15
CPUSchedulingPolicy=fifo
CPUSchedulingPriority=50
ExecStartPre=/bin/bash -c 'taskset -cp 3 $$BASHPID || true'
```

Reload and reboot:

```bash
sudo systemctl daemon-reload
sudo reboot
```

### 4. Install Klipper, Moonraker, and Mainsail

```bash
cd ~
git clone https://github.com/dw-0/kiauh.git
./kiauh/kiauh.sh
```

Install:

1. Klipper
2. Moonraker
3. Mainsail

### 5. Patch `toolhead.py` for lower latency

Back up and inspect:

```bash
cp ~/klipper/klippy/toolhead.py ~/klipper/klippy/toolhead.py.bak
grep -n "BUFFER_TIME" ~/klipper/klippy/toolhead.py
grep -n "flush\|FLUSH\|lookahead\|LOOKAHEAD\|junction" ~/klipper/klippy/toolhead.py | head -30
```

Reduce the buffering constants to approximately:

```python
BUFFER_TIME_LOW = 0.050
BUFFER_TIME_HIGH = 0.150
MOVE_BATCH_TIME = 0.010
```

If present, reduce the look-ahead flush threshold to `0.010` as well, then restart Klipper:

```bash
sudo systemctl restart klipper
journalctl -u klipper -f
```

### 6. Build and flash the Octopus firmware

Run:

```bash
cd ~/klipper
make menuconfig
make clean
make -j4
```

Use:

- Architecture: `STMicroelectronics STM32`
- Processor model: `STM32F446`
- Bootloader offset: `32KiB bootloader`
- Clock reference: `12 MHz crystal`
- Communication interface: `USB (on PA11/PA12)`

Copy `out/klipper.bin` to a FAT32 SD card, rename it to `firmware.bin`, insert it into the Octopus, and power cycle the board.

### 7. Configure Moonraker

Update `~/printer_data/config/moonraker.conf`:

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
```

Restart:

```bash
sudo systemctl restart moonraker
```

### 8. Expected latency

Approximate command latency for this setup:

- Baseline Klipper over HTTP: about `350 ms`
- WebSocket only: about `250 ms`
- WebSocket with `toolhead.py` patch: about `40 ms`
- WebSocket with patch plus CPU isolation: about `15-20 ms` median

## Notes

- These tuning values are intended for a discrete liquid handler, not a high-speed 3D printer.
- If motion becomes hesitant, relax `BUFFER_TIME_LOW` upward.
- `config/default.yaml` is a starting point and should be calibrated to the real deck geometry and pipette mechanics.
