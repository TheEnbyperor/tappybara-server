import redis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver
import vas.models


class Device(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    device_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    authorized = models.BooleanField(default=False)
    config_group = models.ForeignKey(vas.models.ConfigGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices")

    def __str__(self):
        short_device_id = self.device_id_str()[:11]
        if self.name:
            return f"{self.name} ({short_device_id})"
        return short_device_id

    def device_id_str(self):
        return ":".join(f"{d:02X}" for d in self.device_id)

    def public_key_str(self):
        pub = serialization.load_der_public_key(self.public_key)
        lines = []
        if isinstance(pub, rsa.RSAPublicKey):
            n = pub.public_numbers().n
            e = pub.public_numbers().e
            lines.append("RSA:")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Size: {pub.key_size} bits")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Public exponent (e): {e}")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Modulus (n): 0x{n:x}")
        elif isinstance(pub, ec.EllipticCurvePublicKey):
            nums = pub.public_numbers()
            lines.append("ECC")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Curve: {pub.curve.name}")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0X: 0x{nums.x:X}")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Y: 0x{nums.y:X}")
        elif isinstance(pub, ed25519.Ed25519PublicKey):
            lines.append("Ed25519")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Raw key: {pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()}")
        elif isinstance(pub, ed448.Ed448PublicKey):
            lines.append("Ed448")
            lines.append(f"\u00A0\u00A0\u00A0\u00A0Raw key: {pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()}")
        else:
            lines.append(str(type(pub).__name__))
        return "\n".join(lines)


    device_id_str.short_description = "Device ID"
    public_key_str.short_description = "Public key"


@receiver(post_save,   sender=Device)
@receiver(post_save,   sender=vas.models.ConfigGroup)
@receiver(post_save,   sender=vas.models.AppleVASConfiguration)
@receiver(m2m_changed, sender=vas.models.AppleVASConfiguration)
@receiver(post_save,   sender=vas.models.ApplePass)
@receiver(post_save,   sender=vas.models.ApplePassKey)
@receiver(post_delete, sender=vas.models.ApplePassKey)
@receiver(post_save,   sender=vas.models.GoogleSmartTapConfiguration)
@receiver(post_save,   sender=vas.models.GoogleSmartTapCollector)
@receiver(post_save,   sender=vas.models.GoogleSmartTapService)
@receiver(post_delete, sender=vas.models.GoogleSmartTapService)
def device_update(instance, **_kwargs):
    transaction.on_commit(lambda: send_updated_device_config())


def send_updated_device_config():
    print("Send updated device config")
    r = redis.StrictRedis(
        host=settings.REDIS_SERVER, port=settings.REDIS_PORT, db=settings.REDIS_DB
    )
    r.publish("device_config_update", b"")
    r.close()
