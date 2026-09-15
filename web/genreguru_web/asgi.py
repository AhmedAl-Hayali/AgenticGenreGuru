"""ASGI entrypoint for the GenreGuru web application.

When async views land (ADR-0009 follow-up), replace this WSGI-based
ASGI handler with an async-capable server (uvicorn or granian).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "genreguru_web.settings.development")

from genreguru_web.runtime import init_runtime  # noqa: E402

init_runtime()

application = get_asgi_application()
