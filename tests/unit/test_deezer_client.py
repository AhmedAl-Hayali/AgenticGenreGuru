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

Tests import from `genreguru.deezer.client` and mock all httpx
calls via pytest's function-scoped `monkeypatch`; cases are collapsed with
`@pytest.mark.parametrize`.
"""

import re

import httpx
import pytest

from genreguru.deezer import client
from genreguru.errors import GenreguruError, MissingISRCError, PreviewUnavailableError

_QUERY = "Daft Punk"

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


def _response(status_code: int, json: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json,
        request=httpx.Request("GET", _SEARCH_URL),
    )


def _ok_response(data: list[dict]) -> httpx.Response:
    return _response(200, json={"data": data, "total": len(data)})


def _error_response(status: int) -> httpx.Response:
    return _response(status)


def _stub_http(monkeypatch, response: httpx.Response) -> None:
    """Point the client's `httpx.get` at *response*; `monkeypatch` reverts it."""
    monkeypatch.setattr("genreguru.deezer.client.httpx.get", lambda *a, **kw: response)


def _capture_http(monkeypatch, response: httpx.Response) -> list[tuple[tuple, dict]]:
    """Record `httpx.get` calls for *response*, returning `(args, kwargs)` pairs."""
    calls: list[tuple[tuple, dict]] = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        return response

    monkeypatch.setattr("genreguru.deezer.client.httpx.get", fake_get)
    return calls


def _search(monkeypatch, data: list[dict]) -> list[dict]:
    """Stub `httpx.get` with a 200 envelope for *data* and dispatch `client.search`."""
    _stub_http(monkeypatch, _ok_response(data))
    return client.search(_QUERY)


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
        "obj, field, expected",
        [
            ("artist", "id", 27),
            ("artist", "name", "Daft Punk"),
            ("album", "id", 302127),
            ("album", "title", "Discovery"),
        ],
    )
    def test_nested_object_mapped(self, monkeypatch, obj, field, expected):
        """Deezer `artist`/`album` sub-objects must include their fields."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result[obj][field] == expected

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

    def test_search_calls_search_endpoint(self, monkeypatch):
        """`search` must hit the documented Deezer search URL."""
        calls = _capture_http(monkeypatch, _ok_response([]))
        client.search(_QUERY)
        (args, _kwargs) = calls[0]
        assert args[0] == _SEARCH_URL

    def test_search_sends_query_and_limit(self, monkeypatch):
        """`search` must send `q` and `limit=5` as query params."""
        calls = _capture_http(monkeypatch, _ok_response([]))
        client.search(_QUERY)
        (_args, kwargs) = calls[0]
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
        _stub_http(monkeypatch, _response(200, json=body))
        assert client.search(_QUERY) == []


class TestHTTPError:
    """Verify non-2xx statuses propagate via `raise_for_status`."""

    @pytest.mark.parametrize("status", [400, 404, 500])
    def test_non_2xx_raises(self, monkeypatch, status):
        """A non-success HTTP status must raise HTTPStatusError."""
        _stub_http(monkeypatch, _error_response(status))
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

    @pytest.mark.parametrize("code", [4, 700])
    def test_retryable(self, code):
        """QUOTA (4) / SERVICE_BUSY (700) must be classified as retryable."""
        assert client.classify_error(code) is True

    @pytest.mark.parametrize("code", [100, 200, 300, 500, 501, 600, 800, 901])
    def test_non_retryable_raises(self, code):
        """Non-retryable codes must raise GenreguruError and preserve the code."""
        with pytest.raises(GenreguruError) as exc_info:
            client.classify_error(code)
        assert exc_info.value.code == code
