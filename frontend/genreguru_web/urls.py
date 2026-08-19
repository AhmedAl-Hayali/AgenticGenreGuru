"""Top-level URL routing for the GenreGuru web application."""

from django.urls import include, path

urlpatterns = [
    path("", include("fingerprint_app.urls")),
]
