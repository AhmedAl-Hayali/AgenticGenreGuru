"""Shared, environment-agnostic Django settings.

Values that vary between environments come from the Hydra `django` config
group ([`config/django/*.yaml`](https://github.com/AhmedAl-Hayali/AgenticGenreGuru/tree/main/config/django))
via `genreguru.config`. The DB connection comes from the Hydra `db` group
(`cfg.db.*`) so Django and the core library share one connection source.
`.development`, `.production`, and `.test` import these and override
only what differs.
"""

from pathlib import Path

from omegaconf import OmegaConf

from genreguru.config import get_config
from genreguru.gglogging import LoggingManager

BASE_DIR = Path(__file__).resolve().parent.parent.parent

cfg = get_config()

DEBUG = bool(cfg.django.debug)

ALLOWED_HOSTS: list[str] = [h.strip() for h in cfg.django.allowed_hosts.split(",")]

SECRET_KEY = cfg.django.secret_key

SECURE_SSL_REDIRECT = bool(cfg.django.secure_ssl_redirect)
SESSION_COOKIE_SECURE = bool(cfg.django.session_cookie_secure)
CSRF_COOKIE_SECURE = bool(cfg.django.csrf_cookie_secure)
X_FRAME_OPTIONS = cfg.django.x_frame_options


def _databases_from_components(
    dialect: str, database: str, user: str, password: str, host: str, port: int
) -> dict[str, dict[str, str | int]]:
    """Build the Django `DATABASES` dict from individual db config components.

    Reads `dialect`, `driver`, `user`, `password`, `host`, `port`,
    `database` from `cfg.db`.
    """
    return {
        "default": {
            "ENGINE": f"django.db.backends.{dialect}",
            "NAME": database,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": port,
        }
    }


DATABASES = _databases_from_components(
    cfg.db.dialect,
    cfg.db.database,
    cfg.db.user,
    cfg.db.password,
    cfg.db.host,
    cfg.db.port,
)

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

_logging_manager = LoggingManager()
_logging_manager.setup(cfg.logging)
