from django.contrib import admin
from . import models, forms


class ApplePassKeyAdmin(admin.TabularInline):
    model = models.ApplePassKey
    verbose_name = "Apple Pass private key"
    extra = 1
    readonly_fields = ('key_id_str',)
    form = forms.ApplePassKeyForm


@admin.register(models.ApplePass)
class ApplePassAdmin(admin.ModelAdmin):
    inlines = [ApplePassKeyAdmin]


@admin.register(models.AppleVASConfiguration)
class AppleVASConfigurationAdmin(admin.ModelAdmin):
    pass


class GoogleSmartTapServiceAdmin(admin.TabularInline):
    model = models.GoogleSmartTapService
    verbose_name = "Requested service"
    extra = 1


@admin.register(models.GoogleSmartTapConfiguration)
class GoogleSmartTapConfigurationAdmin(admin.ModelAdmin):
    inlines = [GoogleSmartTapServiceAdmin]


@admin.register(models.GoogleSmartTapCollector)
class GoogleSmartTapCollectorAdmin(admin.ModelAdmin):
    form = forms.GoogleSmartTapCollectorForm



@admin.register(models.ConfigGroup)
class ConfigGroupAdmin(admin.ModelAdmin):
    pass
