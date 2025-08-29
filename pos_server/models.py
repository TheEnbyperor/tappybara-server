import string
from django.db import models
from django.utils.crypto import get_random_string

def generate_serial():
    serial = get_random_string(allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ0123456789', length=16)
    while Device.objects.filter(unique_serial=serial).exists():
        serial = get_random_string(allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ0123456789', length=16)
    return serial


def generate_initialization_token():
    token = get_random_string(length=16, allowed_chars=string.ascii_lowercase + string.digits)
    while Device.objects.filter(initialization_token=token).exists():
        token = get_random_string(length=16, allowed_chars=string.ascii_lowercase + string.digits)
    return token


async def generate_api_token():
    token = get_random_string(length=64, allowed_chars=string.ascii_lowercase + string.digits)
    while await Device.objects.filter(api_token=token).aexists():
        token = get_random_string(length=64, allowed_chars=string.ascii_lowercase + string.digits)
    return token


class Device(models.Model):
    unique_serial = models.CharField(max_length=255, default=generate_serial, unique=True)
    initialization_token = models.CharField(max_length=255, default=generate_initialization_token, unique=True)
    api_token = models.CharField(max_length=255, unique=True, null=True, verbose_name="API Token")
    revoked = models.BooleanField(default=False)
    name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    initialized = models.DateTimeField(verbose_name="Initialized at", null=True, blank=True)

    def __str__(self):
        return f"#{self.unique_serial}: {self.name}"


class WebsocketToken(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    expires = models.DateTimeField()