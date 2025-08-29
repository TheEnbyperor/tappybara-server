from django.contrib import admin
from . import models

@admin.register(models.Device)
class DeviceAdmin(admin.ModelAdmin):
    readonly_fields = (
        "device_id_str",
        "public_key_str",
        "last_seen"
    )
