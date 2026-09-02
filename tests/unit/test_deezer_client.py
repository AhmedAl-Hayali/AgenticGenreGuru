"""Unit tests for Deezer search client.

Covers:
- request construction (`GET /search` with `q` + `limit=5` params),
- field mapping from Deezer Track objects, incl. multiple tracks per response,
- fail-loud on missing ISRC (MissingISRCError) / empty preview
  (PreviewUnavailableError),
- empty results for DATA_NOT_FOUND (per contracts/deezer-api.md),
- HTTP error status propagation via `raise_for_status`, and
- error-code mapping per contracts/deezer-api.md incl. QUOTA(4)/SERVICE_BUSY(700)
  retry classification.

Tests import the `client.DeezerSearchClient` class, exercise a module-level
instance, and fake its `httpx.get` with the shared `tests.http_stubs` helpers
via pytest's function-scoped `monkeypatch`; cases are collapsed with
`@pytest.mark.parametrize`.
"""

import re

import httpx
import pytest

from genreguru.deezer import client
from genreguru.dto import DeezerTrack
from genreguru.errors import (
    GenreguruError,
    MissingISRCError,
    PreviewUnavailableError,
)
from tests.http_stubs import (
    RETRYABLE_CODES,
    capture_get,
    ok_json,
    response,
    stub_get,
)

_QUERY = "Daft Punk"

# Deliberate: mirrors `DEEZER_MATCH` (tests.sample_payloads) without coupling
# the unit suite to the contract fixtures.
_SAMPLE_TRACK = {
    "id": 3135556,
    "title": "Harder, Better, Faster, Stronger",
    "isrc": "GBDUW0000059",
    "duration": 226,
    "preview": "https://cdnt-preview.dzcdn.net/api/1/1/abc/def/0/abc.mp3?hdnea=exp=123",
    "artist": {"id": 27, "name": "Daft Punk"},
    "album": {"id": 302127, "title": "Discovery"},
}

_SEARCH_URL = "https://api.deezer.com/search"
_SECOND_TRACK_ID = 999

_MODULE = "genreguru.deezer.client"

_CLIENT_HTTP_GET = f"{_MODULE}.httpx.get"

_MAX_RETRIES = client._MAX_RETRIES

_CLIENT = client.DeezerSearchClient()


def _ok_search(data: list[dict]) -> httpx.Response:
    """200 search envelope with *data* and a matching `total`."""
    return ok_json({"data": data, "total": len(data)}, _SEARCH_URL)


def _search(monkeypatch, data: list[dict]) -> list[DeezerTrack]:
    """Stub `httpx.get` with a 200 search envelope and dispatch `_CLIENT.search`."""
    stub_get(monkeypatch, _CLIENT_HTTP_GET, _ok_search(data))
    return _CLIENT.search(_QUERY)


class TestFieldMapping:
    """Verify that Deezer Track JSON fields map to internal dict keys."""

    @pytest.mark.parametrize(
        "field, expected",
        [
            ("deezer_id", 3135556),
            ("title", "Harder, Better, Faster, Stronger"),
            ("isrc", "GBDUW0000059"),
            ("duration", 226),
        ],
    )
    def test_scalar_field_mapped(self, monkeypatch, field, expected):
        """Deezer scalar fields must map to the internal dict keys."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result[field] == expected

    @pytest.mark.parametrize(
        "obj, expected",
        [
            ("artist", {"id": 27, "name": "Daft Punk"}),
            ("album", {"id": 302127, "title": "Discovery"}),
        ],
    )
    def test_nested_object_mapped(self, monkeypatch, obj, expected):
        """Deezer `artist`/`album` sub-objects must pass through unchanged."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result[obj] == expected

    def test_preview_mapped(self, monkeypatch):
        """Deezer `preview` URL must pass through unchanged."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result["preview"] == _SAMPLE_TRACK["preview"]

    def test_multiple_tracks_all_mapped(self, monkeypatch):
        """Every track in `data` must be mapped, not just the first."""
        second_track = {**_SAMPLE_TRACK, "id": _SECOND_TRACK_ID}
        results = _search(monkeypatch, [_SAMPLE_TRACK, second_track])
        assert [result["deezer_id"] for result in results] == [
            _SAMPLE_TRACK["id"],
            _SECOND_TRACK_ID,
        ]


class TestRequestShape:
    """Verify request construction per contracts/deezer-api.md §1."""

    @pytest.fixture
    def search_calls(self, monkeypatch):
        """Stub an empty search response, dispatch `_CLIENT.search`, capture calls."""
        calls = capture_get(monkeypatch, _CLIENT_HTTP_GET, _ok_search([]))
        _CLIENT.search(_QUERY)
        return calls

    def test_search_calls_search_endpoint(self, search_calls):
        """`search` must hit the documented Deezer search URL."""
        (args, _) = search_calls[0]
        assert args[0] == _SEARCH_URL

    def test_search_sends_query_and_limit(self, search_calls):
        """`search` must send `q` and `limit=5` as query params."""
        (_, kwargs) = search_calls[0]
        assert kwargs["params"] == {"q": _QUERY, "limit": 5}


class TestEmptyResults:
    """Verify empty search results per DATA_NOT_FOUND handling."""

    @pytest.mark.parametrize(
        "body",
        [{"data": [], "total": 0}, {"total": 0}],
        ids=["empty_data", "missing_data_key"],
    )
    def test_empty_results_returns_empty_list(self, monkeypatch, body):
        """A response without tracks must yield an empty result, not an error."""
        stub_get(monkeypatch, _CLIENT_HTTP_GET, ok_json(body, _SEARCH_URL))
        assert _CLIENT.search(_QUERY) == []


class TestHTTPError:
    """Verify non-2xx statuses propagate via `raise_for_status`."""

    @pytest.mark.parametrize("status", [400, 404, 500])
    def test_non_2xx_raises(self, monkeypatch, status):
        """A non-success HTTP status must raise HTTPStatusError."""
        stub_get(monkeypatch, _CLIENT_HTTP_GET, response(status, url=_SEARCH_URL))
        with pytest.raises(httpx.HTTPStatusError):
            client.search(_QUERY)


class TestMissingISRC:
    """Verify fail-loud behaviour when a track lacks a valid ISRC."""

    @pytest.mark.parametrize(
        "track",
        [
            {k: v for k, v in _SAMPLE_TRACK.items() if k != "isrc"},
            {**_SAMPLE_TRACK, "isrc": ""},
        ],
        ids=["missing_key", "empty_string"],
    )
    def test_missing_isrc_raises(self, monkeypatch, track):
        """A track without a valid ISRC must raise MissingISRCError with its ID."""
        with pytest.raises(MissingISRCError, match=re.escape(str(_SAMPLE_TRACK["id"]))):
            _search(monkeypatch, [track])


class TestPreviewUnavailable:
    """Verify fail-loud behaviour when a track has no preview URL."""

    @pytest.mark.parametrize("preview", ["", None], ids=["empty_string", "null"])
    def test_preview_unavailable_raises(self, monkeypatch, preview):
        """A track without a preview URL must raise PreviewUnavailableError."""
        with pytest.raises(PreviewUnavailableError, match="audio preview unavailable"):
            _search(monkeypatch, [{**_SAMPLE_TRACK, "preview": preview}])


class TestErrorCodeMapping:
    """Verify Deezer error code classification for retry vs. failure."""

    @pytest.mark.parametrize("code", RETRYABLE_CODES)
    def test_retryable(self, code):
        """QUOTA (4) / SERVICE_BUSY (700) must be classified as retryable."""
        assert client.classify_error(code) is True

    @pytest.mark.parametrize("code", [100, 200, 300, 500, 501, 600, 800, 901])
    def test_non_retryable_raises(self, code):
        """Non-retryable codes must raise GenreguruError and preserve the code."""
        with pytest.raises(GenreguruError) as exc_info:
            client.classify_error(code)
        assert exc_info.value.code == code
