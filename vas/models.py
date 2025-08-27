from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


def validate_apple_pass_id(val: str):
    if not val.startswith("pass."):
        raise ValidationError("Pass IDs must start with 'pass.'")


class ConfigGroup(models.Model):
    name = models.CharField(max_length=255)
    apple_vas_configuration = models.ForeignKey(
        "AppleVASConfiguration", on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name="Apple VAS configuration",
        related_name="config_groups",
    )
    google_smart_tap_configuration = models.ForeignKey(
        "GoogleSmartTapConfiguration", on_delete=models.SET_NULL, blank=True, null=True,
        verbose_name="Google Smart Tap configuration",
        related_name="config_groups",
    )

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Config Group"


class AppleVASConfiguration(models.Model):
    name = models.CharField(max_length=255)
    passes = models.ManyToManyField("ApplePass", blank=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Apple VAS Configuration"


class ApplePass(models.Model):
    pass_id = models.CharField(
        max_length=255, unique=True,
        verbose_name="Apple Pass ID",
        validators=[validate_apple_pass_id]
    )

    def __str__(self):
        return str(self.pass_id)

    class Meta:
        verbose_name = "Apple PKPass"
        verbose_name_plural = "Apple PKPasses"


class ApplePassKey(models.Model):
    apple_pass = models.ForeignKey(ApplePass, on_delete=models.CASCADE, related_name="keys")
    key_id = models.BinaryField()
    private_key = models.BinaryField()

    def __str__(self):
        return f"{self.apple_pass.pass_id} - {self.key_id_str()}"

    def key_id_str(self):
        return ":".join(f"{d:02X}" for d in self.key_id)

    key_id_str.short_description = "Key ID"


class GoogleSmartTapConfiguration(models.Model):
    name = models.CharField(max_length=255)
    collector = models.ForeignKey("GoogleSmartTapCollector", on_delete=models.PROTECT, related_name="configs")
    store_location_id = models.PositiveIntegerField(blank=True, null=True)
    merchant_name = models.CharField(max_length=255, blank=True, null=True)
    merchant_category = models.PositiveIntegerField(validators=[
        MaxValueValidator(9999)
    ], help_text="4-digit MCC", blank=True, null=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Google Smart Tap Configuration"


class GoogleSmartTapService(models.Model):
    CHOICES = (
        (0x00, "All services"),
        (0x01, "All services except PPSE"),
        (0x02, "PPSE"),
        (0x03, "Loyalty"),
        (0x04, "Offer"),
        (0x05, "Gift card"),
        (0x06, "Private label card"),
        (0x07, "Event ticket"),
        (0x08, "Flight"),
        (0x09, "Transit"),
        (0x10, "Cloud-based wallet"),
        (0x11, "Mobile marketing platform"),
        (0x12, "Generic"),
        (0x13, "Generic Private Pass"),
        (0x40, "Wallet customer"),
    )

    configuration = models.ForeignKey("GoogleSmartTapConfiguration", on_delete=models.CASCADE, related_name="services")
    service = models.PositiveSmallIntegerField(choices=CHOICES)


class GoogleSmartTapCollector(models.Model):
    name = models.CharField(max_length=255)
    collector_id = models.PositiveIntegerField(validators=[
        MinValueValidator(1), MaxValueValidator(0xFFFFFFFF)
    ], verbose_name="Collector ID")
    key_version = models.PositiveIntegerField(validators=[
        MinValueValidator(1), MaxValueValidator(0xFFFFFFFF)
    ])
    private_key = models.BinaryField()

    def __str__(self):
        return f"{self.name} - {self.collector_id} v{self.key_version}"

    class Meta:
        verbose_name = "Google Smart Tap Collector"
