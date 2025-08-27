from django import forms
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from . import models


class ApplePassKeyForm(forms.ModelForm):
    private_key_pem = forms.CharField(
        widget=forms.Textarea(attrs={
            "cols": 80
        }),
        label='Private Key (PEM)',
        help_text="ECC P-256 private key in PEM format",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['private_key_pem'].initial = "REDACTED"

    def clean_private_key_pem(self):
        private_key_pem = self.cleaned_data['private_key_pem']
        if private_key_pem == "REDACTED":
            return None
        try:
            private_key = serialization.load_pem_private_key(private_key_pem.encode(), None)
        except ValueError:
            raise forms.ValidationError("Invalid private key")
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            raise forms.ValidationError("Private key must be ECC")
        if private_key.curve.name != "secp256r1":
            raise forms.ValidationError("Private key must be on the P-256 curve")
        return private_key

    def save(self, commit=True):
        if private_key := self.cleaned_data['private_key_pem']:
            h = hashes.Hash(hashes.SHA256())
            h.update(private_key.public_key().public_numbers().x.to_bytes(32, "big"))
            self.instance.key_id = h.finalize()[:4]
            self.instance.private_key = private_key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()
            )
        return super().save(commit)

    class Meta:
        model = models.ApplePassKey
        fields = ()


class GoogleSmartTapCollectorForm(forms.ModelForm):
    private_key_pem = forms.CharField(
        widget=forms.Textarea(attrs={
            "cols": 80
        }),
        label='Private Key (PEM)',
        help_text="ECC P-256 private key in PEM format",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['private_key_pem'].initial = "REDACTED"

    def clean_private_key_pem(self):
        private_key_pem = self.cleaned_data['private_key_pem']
        if private_key_pem == "REDACTED":
            return None
        try:
            private_key = serialization.load_pem_private_key(private_key_pem.encode(), None)
        except ValueError:
            raise forms.ValidationError("Invalid private key")
        if not isinstance(private_key, ec.EllipticCurvePrivateKey):
            raise forms.ValidationError("Private key must be ECC")
        if private_key.curve.name != "secp256r1":
            raise forms.ValidationError("Private key must be on the P-256 curve")
        return private_key

    def save(self, commit=True):
        if private_key := self.cleaned_data['private_key_pem']:
            self.instance.private_key = private_key.private_bytes(
                serialization.Encoding.DER,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()
            )
        return super().save(commit)

    class Meta:
        model = models.GoogleSmartTapCollector
        fields = (
            "name",
            "collector_id",
            "key_version",
        )
        widgets = {
            "collector_id": forms.TextInput(),
            "key_version": forms.TextInput(),
        }