"""Django views for the `fingerprint_app` track fingerprint search.

Search (`GET /api/search/?query={song_title}`) and Confirm
(`POST /api/confirm/`) endpoints per
`specs/001-song-fingerprint-engine/contracts/search-api.md`.
"""

import json
import logging

from django.http import JsonResponse
from sqlalchemy.orm import Session

from genreguru import fingerprint_service
from genreguru.db.engine import get_session_factory
from genreguru.db.repositories import SongRepository
from genreguru.deezer.client import DeezerSearchClient
from genreguru.errors import (
    AudioProcessingError,
    NetworkDisconnectedError,
    TrackNotFoundError,
)

logger = logging.getLogger(__name__)

_deezer = DeezerSearchClient()

TOP_MATCHES = 5


def _error_response(status: int, error: str) -> JsonResponse:
    """Build an error envelope `{"status": "error", "error": ...}`."""
    return JsonResponse({"status": "error", "error": error}, status=status)


def _get_session() -> Session:
    factory = get_session_factory()
    return factory()


def search_view(request):
    """Return top-5 Deezer matches for a song-title query.

    `GET /api/search/?query={song_title}`.

    Returns:
        JsonResponse: Top-5 matches (status 200) or an error response:
        404 `TrackNotFoundError` / empty query, 503
        `NetworkDisconnectedError`.
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

    return JsonResponse({"status": "success", "matches": matches[:TOP_MATCHES]})


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

    required_fields = (
        "deezer_id",
        "title",
        "isrc",
        "duration",
        "preview",
        "artist",
        "album",
    )
    if not isinstance(body, dict) or any(key not in body for key in required_fields):
        return _error_response(400, "invalid request body")

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
