import asyncio
from pathlib import Path
from klipper_lh.config import MoonrakerConfig
from klipper_lh.moonraker import MoonrakerClient

async def build():
    config = MoonrakerConfig.from_yaml(Path(r"/config/moonraker_ethernet.yaml"))
    client = MoonrakerClient(config)
    await client.connect()
    return client

async def main():
    client = await build()
    info = await client.request("printer.info")
    print("State:", info["state"])

    command_1 = {"script": "FORCE_MOVE STEPPER=stepper_y DISTANCE=-500 VELOCITY=100"}
    info = await client.request(method="printer.gcode.script", params=command_1)
    print(info)

    commands = await client.request("printer.gcode.help")
    print(commands)

if __name__ == "__main__":
    asyncio.run(main())
