"""Django application configuration for the track fingerprint searching application `fingerprint_app`."""

from django.apps import AppConfig


class FingerprintAppConfig(AppConfig):
    """Application config for the fingerprint search UI."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "fingerprint_app"
