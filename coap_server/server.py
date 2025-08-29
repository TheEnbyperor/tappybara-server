import asyncio
import aiocoap.resource
import aiocoap.numbers.contentformat
import zeroconf
import socket
import redis
import tappybara
from django.conf import settings
from . import coap, views

class WhoAmI(aiocoap.resource.Resource):
    @staticmethod
    async def render_get(request):
        text = [
            "Used protocol: %s." % request.remote.scheme,
            "Request came from %s." % request.remote.hostinfo,
            "The server address used %s." % request.remote.hostinfo_local
        ]

        claims = list(request.remote.authenticated_claims)
        if claims:
            text.append(
                "Authenticated claims of the client: %s."
                % ", ".join(repr(c) for c in claims)
            )
        else:
            text.append("No claims authenticated.")

        return aiocoap.Message(
            payload="\n".join(text).encode("utf8"),
            content_format=aiocoap.ContentFormat.by_media_type("text/plain; charset=utf-8")
        )

async def run_server(address: str, port: int):
    root = aiocoap.resource.Site()

    redis_client = redis.asyncio.ConnectionPool(
        host=settings.REDIS_SERVER, port=settings.REDIS_PORT, db=settings.REDIS_DB
    )

    root.add_resource(["whoami"], WhoAmI())
    root.add_resource(["config"], views.DeviceConfig(redis_client))
    root.add_resource(["tap"], views.TapResult(redis_client))
    root.add_resource([".well-known", "core"], aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

    coap.CoAPServer(root, coap.CoAPDTLS, (address, port))

    zc = zeroconf.Zeroconf(
        ip_version=zeroconf.IPVersion.V6Only
    )
    service_info = zeroconf.ServiceInfo(
        type_="_vas-coaps._udp.local.",
        name=f"{settings.COAPS_SERVER_NAME}._vas-coaps._udp.local.",
        port=5684,
        server=f"{socket.gethostname().split('.')[0]}.local.",
        properties={
            "version": tappybara.__version__,
        }
    )
    await zc.async_register_service(service_info)

    print("Listening on %s port %d" % (address, port))
    await asyncio.get_running_loop().create_future()