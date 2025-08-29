import asyncio
import datetime
import redis
import threading
import json
from django.utils import timezone
from django.conf import settings
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import coap_server.models
from . import models

class DeviceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.scope["loop"] = asyncio.get_running_loop()

        self.scope["redis_client"] = redis.StrictRedis(
            host=settings.REDIS_SERVER, port=settings.REDIS_PORT, db=settings.REDIS_DB
        )
        self.scope["redis_pubsub"] = self.scope["redis_client"].pubsub()
        self.scope["redis_pubsub"].subscribe("device_update")
        self.scope["redis_pubsub"].subscribe("tap_redemption")

        t = threading.Thread(target=self.handle_pubsub, daemon=True)
        t.start()

        await self.accept()

    def handle_pubsub(self):
        for message in self.scope["redis_pubsub"].listen():
            if message["type"] != "message":
                continue

            channel = message["channel"]
            if channel == b"device_update":
                self.scope["loop"].call_soon_threadsafe(self.scope["loop"].create_task, self.send_devices())
            elif channel == b"tap_redemption":
                tap_data = json.loads(message["data"])
                self.scope["loop"].call_soon_threadsafe(self.scope["loop"].create_task, self.send_tap_redemption(tap_data))

        self.scope["redis_client"].close()

    async def disconnect(self, close_code):
        self.scope["redis_pubsub"].unsubscribe("device_update")
        self.scope["redis_pubsub"].unsubscribe("tap_redemption")

    async def receive_json(self, data, **kwargs):
        if "command" not in data:
            await self.close(reason="No command")
            return

        command = data["command"]

        if "device" not in self.scope:
            if command != "login":
                await self.close(reason="First command not a login")
                return
            if "token" not in data:
                await self.close(reason="No login token")
                return
            try:
                token = await models.WebsocketToken.objects.aget(token=data["token"])
            except models.WebsocketToken.DoesNotExist:
                await self.close(reason="Invalid login token")
                return

            if token.expires < timezone.now():
                await self.close(reason="Login token expired")
                return

            self.scope["device"] = await models.Device.objects.aget(pk=token.device_id)
            await token.adelete()
            return
        elif command == "login":
            await self.close(reason="Already logged in")
            return

        if command == "get_device":
            await self.send_devices()
        elif command == "bind_device":
            if "id" not in data:
                await self.close(reason="Missing device ID")
                return
            self.scope["bound_device_id"] = int(data["id"])
        else:
            await self.close(reason="Invalid command")

    async def send_devices(self):
        devices = []
        now = timezone.now()
        async for device in coap_server.models.Device.objects.filter(authorized=True):
            devices.append({
                "id": device.pk,
                "name": str(device),
                "device_id": device.device_id_str(),
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "online": device.last_seen + datetime.timedelta(minutes=1) >= now if device.last_seen else False,
            })
        await self.send_json({
            "response": "devices",
            "devices": devices
        })

    async def send_tap_redemption(self, data):
        if data["device_id"] != self.scope.get("bound_device_id"):
            return
        await self.send_json({
            "response": "tap_redemption",
            "data": data["data"]
        })
