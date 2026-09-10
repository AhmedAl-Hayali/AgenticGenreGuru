"""Django views for the `fingerprint_app` track fingerprint search.

Search (`GET /api/search/?query={song_title}`) and Confirm
(`POST /api/confirm/`) endpoints per
`specs/001-song-fingerprint-engine/contracts/search-api.md`.
"""

import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from genreguru import fingerprint_service
from genreguru.audio.features import Feature
from genreguru.db.engine import get_session_factory
from genreguru.db.repositories import SongRepository
from genreguru.deezer.client import DeezerClient
from genreguru.dto import Artist, ConfirmTrack
from genreguru.errors import (
    AudioProcessingError,
    MissingISRCError,
    NetworkDisconnectedError,
    PreviewUnavailableError,
    TrackNotFoundError,
)

logger = logging.getLogger(__name__)

_deezer = DeezerClient()

TOP_MATCHES = 5

FEATURE_LABELS = {f.value: f.label for f in Feature}
"""UI display labels for the `Feature` enum. Built once at import time."""


def _api_config() -> dict:
    """Build the client bootstrap config shared by all UI pages.

    Served as the `#api-config` JSON blob
    ([`json_script`](https://docs.djangoproject.com/en/stable/ref/templates/builtins/#json_script));
    carries the search URL, the confirm URL (the matched track lives in the
    request body — no id in the path), and the feature display labels the UI
    renders (single source: `Feature`).
    """
    return {
        "searchPattern": reverse("search"),
        "confirmUrl": reverse("confirm"),
        "featureLabels": FEATURE_LABELS,
    }


def _error_response(status: int, error: str) -> JsonResponse:
    """Build an error envelope `{"status": "error", "error": ...}`."""
    return JsonResponse({"status": "error", "error": error}, status=status)


def index_view(request):
    """Render the 2-click song search & confirm page.

    `GET /`. Serves `fingerprint_app/index.html`, which drives the search
    (`GET /api/search/`) and confirm (`POST /api/confirm/`) endpoints via the
    `ts/pages/index-page.ts` bootstrap (bundled to `app.js`). The `api_config`
    context is emitted as the `#api-config` JSON blob.
    """
    return render(
        request,
        "fingerprint_app/index.html",
        {
            "api_config": _api_config(),
            "page_title": "GenreGuru — Song Fingerprint Engine",
            "page_subtitle": (
                "Search a song, click a match once to select, click it again "
                "to confirm and fingerprint it."
            ),
        },
    )


@require_GET
def search_view(request):
    """Return top-5 Deezer matches for a song-title query.

    `GET /api/search/?query={song_title}`.

    Returns:
        JsonResponse: Top-5 matches (status 200) or an error response:
        404 `TrackNotFoundError` / empty query, 503
        `NetworkDisconnectedError`, 500 on an upstream data-integrity
        failure (`MissingISRCError` / `PreviewUnavailableError`).
    """
    query = request.GET.get("query", "").strip()
    if not query:
        return _error_response(404, "TrackNotFoundError")

    try:
        matches = _deezer.search(query)
    except TrackNotFoundError:
        return _error_response(404, "TrackNotFoundError")
    except NetworkDisconnectedError:
        return _error_response(503, "NetworkDisconnectedError")
    except MissingISRCError, PreviewUnavailableError:
        logger.exception("unexpected error in search_view")
        return _error_response(500, "internal server error")

    return JsonResponse({"status": "success", "matches": matches[:TOP_MATCHES]})


def _get_session():
    factory = get_session_factory()
    return factory()


def _artists_valid(value: object) -> TypeGuard[list[Artist]]:
    """Return whether *value* is a non-empty list of canonical Artist maps."""
    if not isinstance(value, list) or not value:
        return False
    return all(
        isinstance(artist, dict)
        and isinstance(artist.get("id"), int)
        and isinstance(artist.get("name"), str)
        and bool(artist["name"])
        for artist in value
    )


@require_POST
def confirm_view(request):
    """Process a confirmed 2-click selection into a stored fingerprint.

    `POST /api/confirm/`. The request body carries the selected match
    object (deezer_id, title, isrc, duration, preview, artist, album); no
    id appears in the path — the body is the single source of the selection.

    Returns:
        JsonResponse: The fingerprint payload (status 201) or an error
        response: 400 `AudioProcessingError` / invalid body, 503
        `NetworkDisconnectedError`, 500 on unexpected failure.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError, ValueError:
        return _error_response(400, "invalid JSON body")

    if (
        not isinstance(body, dict)
        or set(body) != set(ConfirmTrack.__required_keys__)
        or not _artists_valid(body.get("artists"))
    ):
        return _error_response(400, "invalid request body")

    body = ConfirmTrack(body)
    session = _get_session()
    try:
        repo = SongRepository(session)
        result = fingerprint_service.process_fingerprint(session, body, repo)
    except AudioProcessingError:
        session.rollback()
        return _error_response(400, "AudioProcessingError")
    except NetworkDisconnectedError:
        session.rollback()
        return _error_response(503, "NetworkDisconnectedError")
    except Exception:
        session.rollback()
        logger.exception("unexpected error in confirm_view")
        return _error_response(500, "internal server error")
    finally:
        session.close()

    return JsonResponse(result, status=201)
