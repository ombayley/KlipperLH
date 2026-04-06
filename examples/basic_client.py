import asyncio
from pathlib import Path
from src.lh.config import load_config
from src.lh.client import MoonrakerClient

async def build():
    config = load_config(Path(r"C:\Users\OllyBayley\Documents\Repos\personal\KlipperLH\src\device_config\default.yaml"))
    client = MoonrakerClient(config.moonraker)
    await client.connect()
    await client.wait_ready()
    return client

async def main():
    client = await build()

    command_1 = {"script": "FORCE_MOVE STEPPER=stepper_y DISTANCE=-500 VELOCITY=100"}
    # result = await client.rpc(method="printer.gcode.script", params=command_1)
    # print(result)

    command_2 = {"script": "FORCE_MOVE STEPPER=stepper_x DISTANCE=500 VELOCITY=100"}
    # result = await client.rpc(method="printer.gcode.script", params=command_2)
    # print(result)

    task_1 = asyncio.create_task(client.rpc(method="printer.gcode.script", params=command_1))
    task_2 = asyncio.create_task(client.rpc(method="printer.gcode.script", params=command_2))
    result_1, result_2 = await asyncio.gather(task_1, task_2)
    print(result_1, result_2)

    # commands = ["FORCE_MOVE STEPPER=stepper_y DISTANCE=500 VELOCITY=100", "FORCE_MOVE STEPPER=stepper_y DISTANCE=-500 VELOCITY=100"]
    # commands = "\n".join(commands)
    # result = await client.rpc(method="printer.gcode.script", params={"script": commands})
    # print(result)

if __name__ == "__main__":
    asyncio.run(main())