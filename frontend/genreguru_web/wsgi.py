"""WSGI entrypoint for the GenreGuru web application."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "genreguru_web.settings.development")

application = get_wsgi_application()
