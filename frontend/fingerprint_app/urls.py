"""URL routing for the track fingerprint searching application `fingerprint_app`."""

from django.urls import path

from . import views

urlpatterns = [
    path("api/search/", views.search_view, name="search"),
    path("api/confirm/", views.confirm_view, name="confirm"),
]
