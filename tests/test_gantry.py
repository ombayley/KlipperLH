import asyncio

from klipper_lh.devices.gantry import Gantry


class FakeMoonrakerClient:
    def __init__(self):
        self.connected = False
        self.requests = []
        self.notification_handlers = {}

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def request(self, method, params=None):
        self.requests.append((method, params))
        if method == "printer.objects.query":
            return {
                "status": {
                    "toolhead": {
                        "print_time": 1.0,
                        "estimated_print_time": 1.0,
                    },
                },
            }
        return "ok"

    def on_notification(self, method, callback):
        self.notification_handlers.setdefault(method, []).append(callback)
        return self

    def emit_status(self, status):
        for callback in self.notification_handlers.get("notify_status_update", []):
            callback([status])


def test_connect_and_disconnect_delegate_to_client():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        await gantry.connect()
        assert client.connected is True

        await gantry.disconnect()
        assert client.connected is False

    asyncio.run(run())


def test_home_sends_g28():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        await gantry.home()

        assert client.requests == [
            ("printer.gcode.script", {"script": "G28"}),
        ]

    asyncio.run(run())


def test_move_xy_sends_g0_with_x_and_y_axes():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        await gantry._move_xy(x=20, y=50)

        assert client.requests == [
            (
                "printer.objects.subscribe",
                {"objects": {"toolhead": ["estimated_print_time"]}},
            ),
            ("printer.gcode.script", {"script": "G0 X20.000 Y50.000 F1200"}),
            (
                "printer.objects.query",
                {"objects": {"toolhead": ["print_time", "estimated_print_time"]}},
            ),
        ]

    asyncio.run(run())


def test_move_z_sends_g0_with_z_axis():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        await gantry._move_z(12.5)

        assert client.requests == [
            (
                "printer.objects.subscribe",
                {"objects": {"toolhead": ["estimated_print_time"]}},
            ),
            ("printer.gcode.script", {"script": "G0 Z12.500 F600"}),
            (
                "printer.objects.query",
                {"objects": {"toolhead": ["print_time", "estimated_print_time"]}},
            ),
        ]

    asyncio.run(run())


def test_move_xy_completes_after_matching_toolhead_print_time():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        async def delayed_query(method, params=None):
            client.requests.append((method, params))
            if method == "printer.objects.query":
                return {
                    "status": {
                        "toolhead": {
                            "print_time": 5.0,
                            "estimated_print_time": 1.0,
                        },
                    },
                }
            return "ok"

        client.request = delayed_query
        move = asyncio.create_task(gantry._move_xy(x=20, y=50, timeout_s=1.0))

        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert move.done() is False

        client.emit_status({"toolhead": {"estimated_print_time": 5.0}})
        await move

        assert all(
            request != ("printer.gcode.script", {"script": "M400"})
            for request in client.requests
        )

    asyncio.run(run())


def test_enable_motors_sends_m17():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        await gantry.enable_motors()

        assert client.requests == [
            ("printer.gcode.script", {"script": "M17"}),
        ]

    asyncio.run(run())


def test_wait_until_idle_sends_m400():
    async def run():
        client = FakeMoonrakerClient()
        gantry = Gantry(client=client)

        await gantry.wait_until_idle()

        assert client.requests == [
            ("printer.gcode.script", {"script": "M400"}),
        ]

    asyncio.run(run())
