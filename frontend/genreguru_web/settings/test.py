"""Test environment settings, used by pytest-django.

Tests run against an in-memory SQLite database, independent of the
environment-selected `cfg.db.url` connection.
"""

import os

os.environ.setdefault("GENREGURU_ENV", "dev")

from .base import (  # noqa: E401, F401, I001
    BASE_DIR,
    cfg,
    # DEBUG,
    ALLOWED_HOSTS,
    SECRET_KEY,
    SECURE_SSL_REDIRECT,
    SESSION_COOKIE_SECURE,
    CSRF_COOKIE_SECURE,
    X_FRAME_OPTIONS,
    # DATABASES,
    FEATURES,
    INSTALLED_APPS,
    MIDDLEWARE,
    ROOT_URLCONF,
    TEMPLATES,
    WSGI_APPLICATION,
    ASGI_APPLICATION,
    LANGUAGE_CODE,
    TIME_ZONE,
    USE_I18N,
    USE_TZ,
    STATIC_URL,
    STATICFILES_DIRS,
    DEFAULT_AUTO_FIELD,
)

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
