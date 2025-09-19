import abc
import asyncio
import redis.client
import aiocoap.resource
import aiocoap.error
import asn1tools
import json
from cryptography.hazmat.primitives import serialization
from django.conf import settings
import vas.models

aiocoap.ContentFormat.define(65000, media_type="application/vnd.as207960.vas.config+uper")
aiocoap.ContentFormat.define(65001, media_type="application/vnd.as207960.vas.config+jer")
aiocoap.ContentFormat.define(65002, media_type="application/vnd.as207960.vas.tap+uper")
aiocoap.ContentFormat.define(65003, media_type="application/vnd.as207960.vas.tap+jer")

ASN_UPER = asn1tools.compile_files([settings.BASE_DIR / "asn1" / "vas.asn"], "uper")
ASN_JER  = asn1tools.compile_files([settings.BASE_DIR / "asn1" / "vas.asn"], "jer")

CF_CONFIG_UPER = aiocoap.ContentFormat.by_media_type("application/vnd.as207960.vas.config+uper")
CF_CONFIG_JER  = aiocoap.ContentFormat.by_media_type("application/vnd.as207960.vas.config+jer")
CF_TAP_UPER    = aiocoap.ContentFormat.by_media_type("application/vnd.as207960.vas.tap+uper")
CF_TAP_JER     = aiocoap.ContentFormat.by_media_type("application/vnd.as207960.vas.tap+jer")


class ResponseRenderer(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def uper_content_format(self):
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def jer_content_format(self):
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def asn1_data_type(self):
        raise NotImplementedError()

class RequestParser(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def uper_content_format(self):
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def jer_content_format(self):
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def asn1_data_type(self):
        raise NotImplementedError()


def render_response(callback):
    async def wrapper(_self, request):
        data = await callback(_self, request)

        accept = aiocoap.ContentFormat(request.opt.accept) if request.opt.accept else None
        if accept is None or accept == _self.uper_content_format:
            return aiocoap.Message(
                payload=ASN_UPER.encode(_self.asn1_data_type, data),
                content_format=_self.uper_content_format,
            )
        elif accept == _self.jer_content_format:
            return aiocoap.Message(
                payload=ASN_JER.encode(_self.asn1_data_type, data),
                content_format=_self.jer_content_format,
            )
        else:
            return aiocoap.Message(code=aiocoap.Code.NOT_ACCEPTABLE)
    return wrapper


def parse_request(callback):
    async def wrapper(_self, request):
        if not request.opt.content_format:
            raise aiocoap.error.UnsupportedContentFormat()

        content_format = aiocoap.ContentFormat(request.opt.content_format)

        if content_format == _self.uper_content_format:
            try:
                data = ASN_UPER.decode(_self.asn1_data_type, request.payload)
            except asn1tools.DecodeError:
                raise aiocoap.error.BadRequest()
        elif content_format == _self.jer_content_format:
            try:
                data = ASN_JER.decode(_self.asn1_data_type, request.payload)
            except (ValueError, AttributeError, IndexError):
                raise aiocoap.error.BadRequest()
        else:
            raise aiocoap.error.UnsupportedContentFormat()

        return await callback(_self, request, data)

    return wrapper


class DeviceConfig(aiocoap.resource.ObservableResource, ResponseRenderer):
    uper_content_format = CF_CONFIG_UPER
    jer_content_format = CF_CONFIG_JER
    asn1_data_type = "ReaderConfig"

    def __init__(self, redis_pool: redis.asyncio.ConnectionPool):
        super().__init__()
        self.redis = redis_pool
        self.redis_pubsub = None

    async def handle_pubsub(self):
        redis_client = redis.asyncio.Redis(connection_pool=self.redis)
        self.redis_pubsub = redis_client.pubsub()
        await self.redis_pubsub.subscribe("device_config_update")
        async for message in self.redis_pubsub.listen():
            if message["type"] != "message":
                continue

            channel = message["channel"]
            if channel == b"device_config_update":
                self.updated_state()

    def update_observation_count(self, new_count):
        loop = asyncio.get_event_loop()
        if new_count == 0:
            if self.redis_pubsub:
                loop.create_task(self.redis_pubsub.unsubscribe("device_config_update"))
        else:
            loop.create_task(self.handle_pubsub())

    @staticmethod
    def encode_private_key(key: bytes):
        key = serialization.load_der_private_key(key, None)
        return key.private_numbers().private_value.to_bytes(32, "big", signed=False)

    @render_response
    async def render_get(self, request):
        device = request.remote.device
        await device.arefresh_from_db()

        if not device.config_group_id:
            return {}

        config_group = await vas.models.ConfigGroup.objects.aget(id=device.config_group_id)

        out = {}

        if config_group.apple_vas_configuration_id:
            apple_config = await vas.models.AppleVASConfiguration.objects.aget(id=config_group.apple_vas_configuration_id)
            out["appleVASConfig"] = {
                "passes": [{
                    "passId": p.pass_id,
                    "privateKeys": [self.encode_private_key(k.private_key) async for k in p.keys.all()]
                } async for p in apple_config.passes.all()]
            }

        if config_group.google_smart_tap_configuration_id:
            google_config = await vas.models.GoogleSmartTapConfiguration.objects.aget(id=config_group.google_smart_tap_configuration_id)
            collector = await vas.models.GoogleSmartTapCollector.objects.aget(id=google_config.collector_id)
            out["googleSmartTapConfig"] = {
                "collectorId": collector.collector_id,
                "collectorKeyVersion": collector.key_version,
                "collectorPrivateKey": self.encode_private_key(collector.private_key),
                "services": [s.service async for s in google_config.services.all()]
            }
            if google_config.store_location_id:
                out["googleSmartTapConfig"]["storeLocationId"] = google_config.store_location_id
            if google_config.merchant_name:
                out["googleSmartTapConfig"]["merchantName"] = google_config.merchant_name
            if google_config.merchant_category:
                out["googleSmartTapConfig"]["mcc"] = google_config.merchant_category

        return out


class TapResult(aiocoap.resource.Resource, RequestParser):
    uper_content_format = CF_TAP_UPER
    jer_content_format = CF_TAP_JER
    asn1_data_type = "TapData"

    def __init__(self, redis_pool: redis.asyncio.ConnectionPool):
        super().__init__()
        self.redis = redis_pool

    @parse_request
    async def render_post(self, request, data):
        print(f"Got tap from {request.remote.device}: {data}", flush=True)

        if "redemption" in data:
            redis_client = redis.asyncio.Redis(connection_pool=self.redis)

            redemptions = []
            redemption_type, redemption = data["redemption"]
            if redemption_type == "appleVas":
                for pass_data in redemption["passes"]:
                    data_format, data = pass_data["data"]
                    if data_format == "decrypted":
                        try:
                            redemptions.append(data["payload"].decode("utf-8"))
                        except UnicodeDecodeError:
                            pass
                    # TODO: handle data device couldn't decrypt
            elif redemption_type == "googleSmartTap":
                for pass_data in redemption["serviceValues"]:
                    for record_type, record in pass_data["records"]:
                        if record_type == "customer":
                            continue
                        try:
                            redemptions.append(record["redemptionData"].decode("utf-8"))
                        except UnicodeDecodeError:
                            pass

            for redemption in redemptions:
                await redis_client.publish("tap_redemption", json.dumps({
                    "device_id": request.remote.device.pk,
                    "data": redemption
                }))
            await redis_client.aclose()

        return aiocoap.Message(code=aiocoap.Code.CREATED)