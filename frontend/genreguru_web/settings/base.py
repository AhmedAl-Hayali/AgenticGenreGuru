"""Shared, environment-agnostic Django settings.

Values that vary between environments come from the Hydra `django` config
group (`config/django/{dev,prod}.yaml`) via `genreguru.config`. The DB
connection comes from the Hydra `db` group (`cfg.db.url`) so Django and the
core library share one connection source. `development.py`, `production.py`,
and `test.py` import these and override only what differs.
"""

from pathlib import Path
from urllib.parse import unquote, urlparse

from omegaconf import OmegaConf

from genreguru.config import get_config
from genreguru.gglogging import setup_logging

BASE_DIR = Path(__file__).resolve().parent.parent.parent

cfg = get_config()

DEBUG = bool(cfg.django.debug)

ALLOWED_HOSTS: list[str] = [h.strip() for h in cfg.django.allowed_hosts.split(",")]

SECRET_KEY = cfg.django.secret_key

SECURE_SSL_REDIRECT = bool(cfg.django.secure_ssl_redirect)
SESSION_COOKIE_SECURE = bool(cfg.django.session_cookie_secure)
CSRF_COOKIE_SECURE = bool(cfg.django.csrf_cookie_secure)
X_FRAME_OPTIONS = cfg.django.x_frame_options


def _databases_from_url(url: str) -> dict:
    """Build the Django `DATABASES` dict from a connection URL."""
    component = urlparse(url)
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": component.path.lstrip("/"),
            "USER": unquote(component.username or ""),
            "PASSWORD": unquote(component.password or ""),
            "HOST": component.hostname or "localhost",
            "PORT": component.port or "5432",
        }
    }


DATABASES = _databases_from_url(cfg.db.url)

FEATURES = OmegaConf.to_container(cfg.features)

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "fingerprint_app",
]

MIDDLEWARE: list[str] = []

ROOT_URLCONF = "genreguru_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    },
]

WSGI_APPLICATION = "genreguru_web.wsgi.application"
ASGI_APPLICATION = "genreguru_web.asgi.application"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "fingerprint_app" / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

setup_logging()
