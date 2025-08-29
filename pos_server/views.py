import json
import datetime
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from . import models


@csrf_exempt
@require_POST
async def device_initialize(request):
    try:
        data = json.loads(request.body)
    except json.decoder.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)

    if "token" not in data:
        return JsonResponse({"error": "Missing initialization token"}, status=400)

    try:
        device = await models.Device.objects.aget(initialization_token=data["token"])
    except models.Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)

    if device.api_token:
        return JsonResponse({"error": "Device already initialized"}, status=409)

    api_token = await models.generate_api_token()
    device.api_token = api_token
    device.initialized = timezone.now()
    await device.asave()

    return JsonResponse({
        "api_token": device.api_token,
        "unique_serial": device.unique_serial,
        "name": device.name,
    }, status=200)


@csrf_exempt
@require_GET
async def device_websocket_token(request):
    if not "Authorization" in request.headers:
        return JsonResponse({"error": "Missing authorization header"}, status=401)

    auth = request.headers["Authorization"].replace("Device ", "")
    try:
        device = await models.Device.objects.aget(api_token=auth)
    except models.Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=403)

    await models.WebsocketToken.objects.filter(device=device).adelete()
    token = await models.generate_api_token()
    await models.WebsocketToken(
        device=device,
        token=token,
        expires=timezone.now() + datetime.timedelta(minutes=5),
    ).asave()

    return JsonResponse({
        "token": token
    }, status=200)