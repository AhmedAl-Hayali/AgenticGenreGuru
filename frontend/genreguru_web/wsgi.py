"""WSGI entrypoint for the GenreGuru web application."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "genreguru_web.settings.development")

from genreguru_web.runtime import init_runtime  # noqa: E402

init_runtime()

application = get_wsgi_application()
