from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

logs_file_path = "./logs/server.log"
logs_folder_path = "./logs"
if os.name == "nt":
    logs_file_path = logs_file_path
    logs_folder_path = logs_folder_path


def check_logs_path():
    logger.debug("Checking logs path...")
    if not os.path.exists(logs_file_path):
        if not os.path.exists(logs_folder_path):
            os.mkdir(logs_folder_path)
        os.system(f"echo > {logs_file_path}")


# format = "%(asctime)s - %(module)s - %(funcName)s - line:%(lineno)d - %(levelname)s - %(message)s"
logger.add(sys.stderr, level="INFO")
logger.add(logs_file_path, level="DEBUG")

# logger.setLevel(logging.INFO)
# ch = logging.StreamHandler()
# fh = logging.FileHandler(filename=logs_file_path)

# ch.setFormatter(format)
# fh.setFormatter(format)
# logger.addHandler(ch)  # Exporting logs to the screen
# logger.addHandler(fh)  # Exporting logs to a file


try:
    import ujson

    JSON_ENCODER = ujson.dumps
    JSON_DECODER = ujson.loads
except ImportError:
    import json

    JSON_ENCODER = json.dumps
    JSON_DECODER = json.loads


class OPCODES:
    INITIALIZE = 1
    HEARTBEAT = 2
    HEARTBEAT_CONFIRM = 3
    CLOSE_CONNECTION = 4
    MESSAGE = 6
    SEND_MESSAGE = 7


class ConnectionManager:

    logger = logger.bind(module="Manager")
    _callbacks = {}

    def __init__(self):
        self.connected = {}
        self.loop = asyncio.get_event_loop()

        self.heartbeat_interval = 30
        self.heartbeat_timeout = 120
        self._active_keys = set()

    async def _register(self, ws: WebSocket):
        self.logger.info(
            f"New connection from {str(ws.id)} has been registered successfully!",
        )
        if str(ws.id) not in self.connected:
            self.logger.debug(f"Creating timeout task. ID 1")
            self.connected[str(ws.id)] = {
                "last_heartbeat": time.time(),
                "timeout_task": self.loop.create_task(self._timeout_task(ws)),
                "ws": ws,
                "name": None,
            }
        else:
            self.connected[str(ws.id)]["last_heartbeat"] = time.time()
            self.logger.debug(f"Cancelling timeout task. ID 1")
            self.connected[str(ws.id)]["timeout_task"].cancel()
            await asyncio.sleep(0.1)
            self.logger.debug(
                f"Task is cancelled: {self.connected[str(ws.id)]['timeout_task'].cancelled()}"
            )
            self.logger.debug(f"Creating timeout task. ID 2")
            self.connected[str(ws.id)]["timeout_task"] = self.loop.create_task(
                self._timeout_task(ws)
            )

        payload = {
            "op": OPCODES.INITIALIZE,
            "heartbeat_interval": self.heartbeat_interval,
        }
        await ws.send_json(payload)

    async def _unregister(self, ws: WebSocket):
        self.logger.info(
            f"Unregistering {ws.id}| Is registered: {str(ws.id) in self.connected}"
        )
        if d := self.connected.pop(str(ws.id), None):
            self.logger.debug(f"Cancelling timeout task. ID 2")
            d["timeout_task"].cancel()
            await asyncio.sleep(0)
            self.logger.debug(f"Task is cancelled: {d['timeout_task'].cancelled()}")
            if d["name"]:
                self.logger.info(f"Disconnected {d['name']} from {ws.client.host}")
        else:
            self.logger.info(f"Disconnected {ws.client.host}")

    async def _handle_heartbeat(self, ws):
        ws_id = str(ws.id)
        self.connected[ws_id]["last_heartbeat"] = time.time()

    async def _close_ws(self, ws: WebSocket):
        await ws.send_json({"op": OPCODES.CLOSE_CONNECTION})
        await ws.close()

    async def _timeout_task(self, ws: WebSocket):
        while True:
            if not self.connected.get(str(ws.id)):
                self.logger.debug(f"Task is cancelled: {ws.id}")
                return
            try:
                await asyncio.sleep(self.heartbeat_timeout)
                if (
                    time.time() - self.connected[str(ws.id)]["last_heartbeat"]
                    > self.heartbeat_timeout
                ):
                    await self._close_ws(ws)
                    return
            except asyncio.CancelledError:
                logger.debug("Cancelled timeout task")
                raise

    async def _handler(self, ws: WebSocket):
        auth = ws.headers.get("Authorization")
        if auth not in self._active_keys:
            await self._close_ws(ws)
            return

        await self._register(ws)
        ws_id = str(ws.id)
        try:
            while True:
                json_msg = await ws.receive_json()
                self.logger.debug(f"Received from {ws_id}: {json_msg}")

                if isinstance(json_msg, str):
                    await ws.send_json(
                        {
                            "op": OPCODES.MESSAGE,
                            "error": "Invalid JSON",
                            "description": "An invalid json was sent to the server",
                        },
                    )

                if json_msg["op"] == OPCODES.HEARTBEAT:
                    self.logger.info(f"{ws_id} > Heart beat received")
                    await ws.send_json({"op": OPCODES.HEARTBEAT_CONFIRM})
                    await self._handle_heartbeat(ws)

                elif json_msg["op"] == OPCODES.MESSAGE:
                    for callback in self._callbacks.get("on_message", []):
                        args = [json_msg["message"], self.connected[ws_id]["name"]]
                        func = callback["func"]
                        self.loop.create_task(func(*args))

        except WebSocketDisconnect:
            await self._unregister(ws)
            self.logger.info(f"Client {ws.client} with ID #{ws.id} disconnected")

        finally:
            if ws_id in self.connected:
                await self._unregister(ws)

    async def send(self, message: str):
        for i in self.connected.values():
            await i["ws"].send_json({"op": OPCODES.SEND_MESSAGE, "message": message})

    async def wait_for(
        self, wait_type: str, check=None, timeout: int = 60
    ) -> Optional[dict]:
        wait_event = asyncio.Future()

        async def wrapped(message):
            if check(message):
                self.remove_callback(wrapped, callback_type="on_message")
                print(f"{wait_type} > {message}")
                wait_event.set_result(message)

        kwargs = {"func": wrapped, "callback_type": wait_type}

        self.add_callback(**kwargs)
        try:
            return await asyncio.wait_for(wait_event, timeout=timeout)
        except asyncio.TimeoutError:
            self.remove_callback(**kwargs)
            raise asyncio.TimeoutError(f"Timed out waiting for a response")

    def get_ws(self, socket_id: int):
        if socket := self.connected.get(str(socket_id)):
            return socket["ws"]

    @classmethod
    def add_callback(cls, func, callback_type: str = "on_message"):
        cls.logger.info(f"Adding callback {func.__name__}.")
        """
        callback_types:
        - on_message
        - on_disconnect
        """
        try:
            for i in cls.name_to_guild.values():
                cls._callbacks[i][callback_type] = cls._callbacks[i].get(
                    callback_type, []
                )
                cls._callbacks[i][callback_type].append({"func": func})
        except Exception as e:
            cls.logger.error(
                f"Error adding callback {func.__name__} for {callback_type} {e}"
            )

    @classmethod
    def remove_callback(cls, func, callback_type: str = "on_message"):
        cls.logger.info(f"Remove callback {func.__name__}")

        for guild_name, data in cls._callbacks.items():
            for i in data[callback_type]:
                if i["func"] == func:
                    cls._callbacks[guild_name][callback_type].remove(i)

    # def main(self):
    #     self.logger.info("Starting websocket server manager...")
    #     return self


if __name__ != "__main__":
    check_logs_path()
