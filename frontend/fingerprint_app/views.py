"""Django views for the `fingerprint_app` track fingerprint search.

Search (`GET /api/search/?query={song_title}`) endpoint per
`specs/001-song-fingerprint-engine/contracts/search-api.md`.
"""

import logging

from django.http import JsonResponse
from sqlalchemy.orm import Session

from genreguru.db.engine import get_session_factory
from genreguru.deezer.client import DeezerSearchClient
from genreguru.errors import (
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
