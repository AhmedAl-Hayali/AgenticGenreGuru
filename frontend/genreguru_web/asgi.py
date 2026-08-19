"""ASGI entrypoint for the GenreGuru web application."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "genreguru_web.settings.development")

application = get_asgi_application()
