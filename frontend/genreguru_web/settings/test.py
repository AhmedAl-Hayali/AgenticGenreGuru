"""Test environment settings, used by pytest-django.

Tests run against an in-memory SQLite database, independent of the
environment-selected `cfg.db.url` connection.
"""

import os

os.environ.setdefault("GENREGURU_ENV", "dev")

from .base import *  # noqa: E402, F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
