from django.contrib import admin
from . import models

@admin.register(models.Device)
class DeviceAdmin(admin.ModelAdmin):
    readonly_fields = (
        "unique_serial",
        "initialization_token",
        "created",
        "initialized",
    )
    exclude = (
        "api_token",
    )
    fields = (
        "unique_serial",
        "name",
        "revoked",
        "initialization_token",
        "created",
        "initialized",
    )

    def get_fields(self, request, obj=None):
        if obj:
            if obj.api_token:
                return (
                    "unique_serial",
                    "name",
                    "revoked",
                    "created",
                    "initialized",
                )
            else:
                return (
                    "unique_serial",
                    "name",
                    "revoked",
                    "initialization_token",
                    "created",
                    "initialized",
                )
        else:
            return (
                "name",
            )