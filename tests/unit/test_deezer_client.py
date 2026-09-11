"""Unit tests for the Deezer client (search + track lookup).

Covers:
- request construction (`GET /search` with `q` + `limit=5` params, `GET
  /track/{id}`),
- field mapping from Deezer Track objects, incl. multiple tracks per response,
- canonical `artists` mapping: main-first with `contributors` dedupe, tolerant
  skip of malformed rosters, and an `Unknown artist` fallback (list never empty),
- best-effort per-candidate `/track/{id}` roster enrichment inside `search`
  (full-roster merge, per-track failure fallback to the search-form roster) and
  sanitization of results to the `SEARCH_FIELDS` wire shape,
- cover URL building from `md5_image`,
- fail-loud on missing ISRC (MissingISRCError) / empty preview
  (PreviewUnavailableError),
- empty results for DATA_NOT_FOUND search (per contracts/deezer-api.md) and
  `TrackNotFoundError` for a DATA_NOT_FOUND track lookup,
- non-2xx status / unparseable body → `NetworkDisconnectedError` (503), and
- error-code mapping per contracts/deezer-api.md incl. QUOTA(4)/SERVICE_BUSY(700)
  retry classification.

Tests import the `client.DeezerClient` class, exercise a module-level
instance, and fake its `httpx.get` with the shared `tests.http_stubs`
helpers (`route_get`, `stub_get`/`capture_get`) via pytest's
function-scoped `monkeypatch`; cases are collapsed with
`@pytest.mark.parametrize`.
"""

import re
from typing import Any, cast

import httpx
import pytest
from httpx import Response

from genreguru.deezer import client
from genreguru.dto import (
    Album,
    Artist,
    DeezerSearchResponse,
    RawDeezerTrack,
    Track,
)
from genreguru.errors import (
    GenreguruError,
    MissingISRCError,
    NetworkDisconnectedError,
    PreviewUnavailableError,
    TrackNotFoundError,
)
from tests.http_stubs import (
    RETRYABLE_CODES,
    capture_get,
    error_envelope,
    ok_json,
    ok_track,
    repeat,
    response,
    retry_then_success,
    route_get,
    sequence,
    stub_get,
)

_QUERY = "Daft Punk"

_COVER_MD5 = "950fd2a2d0f5f80e3b5f1e9f0b2a3c4d"
_COVER_URL = f"https://cdn-images.dzcdn.net/images/cover/{_COVER_MD5}/300x300.jpg"

_TIMEOUTS = [
    httpx.ConnectTimeout("connection timed out"),
    httpx.ReadTimeout("read timed out"),
]

_MAIN_ARTIST = Artist(id=27, name="Daft Punk")
_EXTRA_ARTIST = Artist(id=11, name="Stardust")
_MAIN_ROSTER = [_MAIN_ARTIST]
_FULL_ROSTER = [_MAIN_ARTIST, _EXTRA_ARTIST]

# Deliberate: mirrors `DEEZER_MATCH` (tests.sample_payloads) without coupling
# the unit suite to the contract fixtures.
_SAMPLE_TRACK = RawDeezerTrack(
    id=3135556,
    title="Harder, Better, Faster, Stronger",
    isrc="GBDUW0000059",
    duration=226,
    preview="https://cdnt-preview.dzcdn.net/api/1/1/abc/def/0/abc.mp3?hdnea=exp=123",
    md5_image=_COVER_MD5,
    artist=_MAIN_ARTIST,
    album=Album(id=302127, title="Discovery"),
)

_SEARCH_URL = "https://api.deezer.com/search"
_TRACK_URL = "https://api.deezer.com/track"
_SECOND_TRACK_ID = 999

_MODULE = "genreguru.deezer.client"

_CLIENT_HTTP_GET = f"{_MODULE}.httpx.get"

_MAX_RETRIES = client._MAX_RETRIES

_CLIENT = client.DeezerClient()


def _ok_search(data: list[RawDeezerTrack]) -> httpx.Response:
    """200 search envelope with *data* and a matching `total`."""
    body: DeezerSearchResponse = {"data": data, "total": len(data)}
    return ok_json(body, _SEARCH_URL)


def _track_url(track_id: int) -> str:
    """The documented Deezer track endpoint for *track_id*."""
    return f"{_TRACK_URL}/{track_id}"


def _raw_track(contributors=None, **overrides) -> RawDeezerTrack:
    """A `RawDeezerTrack` fixture: `_SAMPLE_TRACK` plus *contributors* overrides.

    Mirrors `_SAMPLE_TRACK`'s main-artist search form by default; pass
    `contributors=` (e.g. `_FULL_ROSTER`) when building a `/track/{id}`
    lookup body. Any other key overrides via keyword (e.g. `id=...`,
    `album=None`, `isrc=""`). The single `cast`/`Any` bridge for the whole
    suite: deliberately-malformed values (non-list `contributors`, bad-typed
    entries) aren't `RawDeezerTrack`-legal, and the JSON wire layer is
    genuinely untyped — so this one helper owns the claim, mirroring the
    client's tolerant `.get()` reads.
    """
    body: Any = {**_SAMPLE_TRACK, **overrides}
    if contributors is not None:
        body["contributors"] = contributors
    return cast(RawDeezerTrack, body)


def _search(
    monkeypatch,
    data: list[RawDeezerTrack],
    track_bodies: dict[int, Response] | None = None,
) -> list[Track]:
    """Stub `/search` + a `/track/{id}` lookup per hit, dispatch `_CLIENT.search`.

    Each hit's lookup returns the same body it appeared in `/search` by
    default, so the mapped roster is unchanged by enrichment — mapping and
    validation assertions stay decoupled from the enrichment tests. Pass
    *track_bodies* (track id → response) to override specific
    `/track/{id}` lookups, e.g. richer rosters or failures.
    """
    url_map = {_SEARCH_URL: _ok_search(data)}
    if track_bodies is None:
        track_bodies = {
            track["id"]: ok_track(track, _track_url(track["id"])) for track in data
        }
    url_map.update(
        {_track_url(track_id): body for track_id, body in track_bodies.items()}
    )
    route_get(monkeypatch, _CLIENT_HTTP_GET, url_map)
    return _CLIENT.search(_QUERY)


def _track(monkeypatch, body: RawDeezerTrack) -> Track:
    """Stub `httpx.get` with a 200 track payload and dispatch `_CLIENT.get_track`."""
    track_id = body["id"]
    stub_get(monkeypatch, _CLIENT_HTTP_GET, ok_track(body, _track_url(track_id)))
    return _CLIENT.get_track(track_id)


def _route_search_retry(monkeypatch, search_seq) -> list[tuple[tuple, dict]]:
    """Route `/search` through *search_seq* and the sample track lookup to 200."""
    return route_get(
        monkeypatch,
        _CLIENT_HTTP_GET,
        {
            _SEARCH_URL: search_seq,
            _track_url(_SAMPLE_TRACK["id"]): ok_track(
                _SAMPLE_TRACK, _track_url(_SAMPLE_TRACK["id"])
            ),
        },
    )


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

    def test_artists_mapped_main_first(self, monkeypatch):
        """The canonical `artists` list must lead with the main artist."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result["artists"] == _MAIN_ROSTER

    @pytest.mark.parametrize(
        "album",
        [Album(id=302127, title="Discovery"), None],
    )
    def test_album_passthrough(self, monkeypatch, album):
        """Deezer `album` sub-object must pass through unchanged (or None)."""
        raw = _raw_track(album=album)
        result = _search(monkeypatch, [raw])[0]
        assert result["album"] == album

    def test_cover_mapped(self, monkeypatch):
        """`md5_image` must map to the documented bare-suffix cover URL."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result["cover"] == _COVER_URL

    def test_cover_empty_without_md5_image(self, monkeypatch):
        """A track without `md5_image` must map `cover` to an empty string."""
        raw = _raw_track(md5_image=None)
        result = _search(monkeypatch, [raw])[0]
        assert result["cover"] == ""

    def test_preview_mapped(self, monkeypatch):
        """Deezer `preview` URL must pass through unchanged."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert result["preview"] == _SAMPLE_TRACK["preview"]

    def test_multiple_tracks_all_mapped(self, monkeypatch):
        """Every track in `data` must be mapped, not just the first."""
        second_track = _raw_track(id=_SECOND_TRACK_ID)
        results = _search(monkeypatch, [_SAMPLE_TRACK, second_track])
        assert [result["deezer_id"] for result in results] == [
            _SAMPLE_TRACK["id"],
            _SECOND_TRACK_ID,
        ]


class TestSearchEnrichment:
    """Verify best-effort per-candidate `/track/{id}` roster enrichment in `search`."""

    def test_full_roster_merged(self, monkeypatch):
        """A successful lookup must splice the full main-first contributor roster."""
        track_id = _SAMPLE_TRACK["id"]
        result = _search(
            monkeypatch,
            [_SAMPLE_TRACK],
            {
                track_id: ok_track(
                    _raw_track(contributors=_FULL_ROSTER), _track_url(track_id)
                )
            },
        )[0]
        assert result["artists"] == _FULL_ROSTER

    def test_lookup_failure_keeps_search_form_roster(self, monkeypatch):
        """A failing lookup must keep the search-form (main-artist) roster."""
        track_id = _SAMPLE_TRACK["id"]
        result = _search(
            monkeypatch,
            [_SAMPLE_TRACK],
            {track_id: error_envelope(404, 800, _track_url(track_id))},
        )[0]
        assert result["artists"] == _MAIN_ROSTER

    def test_one_failed_sibling_still_enriched(self, monkeypatch):
        """Only the failed track keeps its search-form roster; siblings stay enriched."""
        second = _raw_track(id=_SECOND_TRACK_ID)
        results = _search(
            monkeypatch,
            [second, _SAMPLE_TRACK],
            {
                second["id"]: error_envelope(404, 800, _track_url(second["id"])),
                _SAMPLE_TRACK["id"]: ok_track(
                    _raw_track(contributors=_FULL_ROSTER),
                    _track_url(_SAMPLE_TRACK["id"]),
                ),
            },
        )
        failed, enriched = results
        assert failed["artists"] == _MAIN_ROSTER
        assert enriched["artists"] == _FULL_ROSTER

    def test_result_sanitized_to_search_fields(self, monkeypatch):
        """Each returned match must carry exactly the `SEARCH_FIELDS` keys."""
        result = _search(monkeypatch, [_SAMPLE_TRACK])[0]
        assert set(result) == set(client.SEARCH_FIELDS)
        assert result["cover"] == _COVER_URL


class TestContributorsMapping:
    """Verify the canonical main-first `artists` dedupe/tolerance contract."""

    def test_track_lookup_main_first_dedupes_contributors(self, monkeypatch):
        """`contributors[0] == main` must yield main first, then the roster."""
        body = _raw_track(contributors=_FULL_ROSTER)
        assert _track(monkeypatch, body)["artists"] == _FULL_ROSTER

    def test_malformed_contributors_skipped(self, monkeypatch):
        """Entries lacking an id/name must be skipped without aborting."""
        body = _raw_track(
            contributors=[
                _MAIN_ARTIST,
                {"id": "not-an-int", "name": "Bad"},
                {"name": "NoId"},
                Artist(id=99, name=""),
                _EXTRA_ARTIST,
            ]
        )
        assert _track(monkeypatch, body)["artists"] == _FULL_ROSTER

    def test_non_list_contributors_ignored(self, monkeypatch):
        """A non-list `contributors` value must fall back to the main artist."""
        body = _raw_track(contributors=Artist(id=1, name="Nope"))
        assert _track(monkeypatch, body)["artists"] == _MAIN_ROSTER

    def test_unknown_artist_fallback_when_main_malformed(self, monkeypatch):
        """A worst-case payload must still yield one `Unknown artist` entry."""
        body = _raw_track(
            artist={"id": "bad", "name": ""},
            contributors=[{"id": 1, "name": None}],
        )
        assert _track(monkeypatch, body)["artists"] == [client._UNKNOWN_ARTIST]


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


class TestGetTrack:
    """Verify the track-lookup path (`GET /track/{id}`) mapping and errors."""

    def test_get_track_hits_track_endpoint_with_id(self, monkeypatch):
        """`get_track` must request `https://api.deezer.com/track/{id}`."""
        calls = capture_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            ok_track(_SAMPLE_TRACK, _track_url(_SAMPLE_TRACK["id"])),
        )
        _CLIENT.get_track(_SAMPLE_TRACK["id"])
        (args, _kwargs) = calls[0]
        assert args[0] == _track_url(_SAMPLE_TRACK["id"])

    def test_track_maps_contributors(self, monkeypatch):
        """`get_track` must carry the full contributor roster (main-first)."""
        body = _raw_track(contributors=_FULL_ROSTER)
        result = _track(monkeypatch, body)
        assert result["artists"] == _FULL_ROSTER

    def test_http_404_data_not_found_raises_track_not_found(self, monkeypatch):
        """A 404 with a DATA_NOT_FOUND (800) envelope must raise `TrackNotFoundError`."""
        track_id = _SAMPLE_TRACK["id"]
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            error_envelope(404, 800, _track_url(track_id)),
        )
        with pytest.raises(TrackNotFoundError) as exc_info:
            _CLIENT.get_track(track_id)
        assert exc_info.value.deezer_id == track_id

    def test_embedded_800_raises_track_not_found(self, monkeypatch):
        """A 200 body embedding code 800 must also raise `TrackNotFoundError`."""
        track_id = _SAMPLE_TRACK["id"]
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            error_envelope(200, 800, _track_url(track_id)),
        )
        with pytest.raises(TrackNotFoundError):
            _CLIENT.get_track(track_id)

    @pytest.mark.parametrize("code", [4, 700])
    def test_retryable_then_success(self, monkeypatch, code):
        """A retryable track-lookup error must retry, then succeed."""
        track_id = _SAMPLE_TRACK["id"]
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            retry_then_success(
                error_envelope(200, code, _track_url(track_id)),
                ok_track(_SAMPLE_TRACK, _track_url(track_id)),
                n_failures=_MAX_RETRIES - 1,
            ),
        )
        assert _CLIENT.get_track(track_id)["deezer_id"] == track_id

    def test_track_missing_isrc_raises(self, monkeypatch):
        """A track without an ISRC must fail loud even on the lookup path."""
        with pytest.raises(MissingISRCError):
            _track(monkeypatch, _raw_track(isrc=""))

    def test_track_non_object_body_raises_network_disconnected(self, monkeypatch):
        """A valid-JSON but non-object track body must map to 503."""
        track_id = _SAMPLE_TRACK["id"]
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            response(
                200,
                content=b"[]",
                headers={"content-type": "application/json"},
                url=_track_url(track_id),
            ),
        )
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.get_track(track_id)
        assert exc_info.value.attempts == 1


class TestEmptyResults:
    """Verify empty search results per DATA_NOT_FOUND handling."""

    @pytest.mark.parametrize(
        "body",
        [
            DeezerSearchResponse(data=[], total=0),
            DeezerSearchResponse(total=0),
        ],
        ids=["empty_data", "missing_data_key"],
    )
    def test_empty_results_returns_empty_list(
        self, monkeypatch, body: DeezerSearchResponse
    ):
        """A response without tracks must yield an empty result, not an error."""
        stub_get(monkeypatch, _CLIENT_HTTP_GET, ok_json(body, _SEARCH_URL))
        assert _CLIENT.search(_QUERY) == []

    def test_data_not_found_404_returns_empty(self, monkeypatch):
        """A 404 carrying a DATA_NOT_FOUND (800) envelope must yield an empty list."""
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            error_envelope(404, 800, _SEARCH_URL),
        )
        assert _CLIENT.search(_QUERY) == []


class TestHTTPError:
    """Verify non-2xx statuses map to a 503 `NetworkDisconnectedError`."""

    def test_non_2xx_raises_network_disconnected(self, monkeypatch):
        """A non-2xx status without an envelope maps to a 503 `NetworkDisconnectedError`."""
        stub_get(monkeypatch, _CLIENT_HTTP_GET, response(500, url=_SEARCH_URL))
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.attempts == 1

    def test_non_2xx_with_error_envelope_exposes_code(self, monkeypatch):
        """A non-2xx status carrying an error envelope maps to 503 and preserves its code."""
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            error_envelope(503, 100, _SEARCH_URL),
        )
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.code == 100
        assert exc_info.value.attempts == 1


class TestSearchTransportErrors:
    """Verify network transport failures map to retry / 503 correctly."""

    @pytest.mark.parametrize(
        "timeout", _TIMEOUTS, ids=["connect_timeout", "read_timeout"]
    )
    def test_timeout_retries_then_success(self, monkeypatch, timeout):
        """A ConnectTimeout/ReadTimeout must be retried, succeeding on the last attempt."""
        search_seq = retry_then_success(
            timeout, _ok_search([_SAMPLE_TRACK]), _MAX_RETRIES - 1
        )
        calls = _route_search_retry(monkeypatch, search_seq)
        results = _CLIENT.search(_QUERY)
        assert [r["deezer_id"] for r in results] == [_SAMPLE_TRACK["id"]]
        search_calls = [call for call in calls if call[0][0] == _SEARCH_URL]
        assert len(search_calls) == _MAX_RETRIES

    @pytest.mark.parametrize(
        "timeout", _TIMEOUTS, ids=["connect_timeout", "read_timeout"]
    )
    def test_timeout_exhausts_budget_sets_code_none(self, monkeypatch, timeout):
        """A budget exhausted only by timeouts must raise with code=None."""
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            repeat(timeout, _MAX_RETRIES),
        )
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.attempts == _MAX_RETRIES
        assert exc_info.value.code is None

    def test_connect_error_raises_immediately(self, monkeypatch):
        """ConnectError must raise without retrying."""
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            sequence(httpx.ConnectError("DNS resolution failed")),
        )
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.attempts == 1

    def test_non_object_body_raises_network_disconnected(self, monkeypatch):
        """A valid-JSON but non-object body (e.g. a list) must map to 503."""
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            response(
                200,
                content=b'["not", "an", "object"]',
                headers={"content-type": "application/json"},
                url=_SEARCH_URL,
            ),
        )
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.attempts == 1


class TestSearchRetry:
    """Verify the retry-with-backoff path for QUOTA / SERVICE_BUSY on search."""

    @pytest.mark.parametrize("code", [4, 700])
    def test_retryable_then_success(self, monkeypatch, code):
        """A retryable Deezer code must be retried, succeeding on the last attempt."""
        search_seq = retry_then_success(
            error_envelope(200, code, _SEARCH_URL),
            _ok_search([_SAMPLE_TRACK]),
            n_failures=_MAX_RETRIES - 1,
        )
        _route_search_retry(monkeypatch, search_seq)
        results = _CLIENT.search(_QUERY)
        assert [r["deezer_id"] for r in results] == [_SAMPLE_TRACK["id"]]

    def test_retryable_exhausts_budget(self, monkeypatch):
        """Repeated retryable codes must exhaust the budget, raising with the code."""
        code = RETRYABLE_CODES[0]
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            repeat(error_envelope(200, code, _SEARCH_URL), _MAX_RETRIES),
        )
        with pytest.raises(NetworkDisconnectedError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.attempts == _MAX_RETRIES
        assert exc_info.value.code == code

    def test_non_retryable_envelope_fails_loudly(self, monkeypatch):
        """A non-retryable Deezer code must fail loudly, preserving the code."""
        stub_get(
            monkeypatch,
            _CLIENT_HTTP_GET,
            error_envelope(200, 500, _SEARCH_URL),
        )
        with pytest.raises(GenreguruError) as exc_info:
            _CLIENT.search(_QUERY)
        assert exc_info.value.code == 500


class TestMissingISRC:
    """Verify fail-loud behaviour when a track lacks a valid ISRC."""

    def test_missing_isrc_raises(self, monkeypatch):
        """A track without a valid ISRC must raise MissingISRCError with its ID."""
        with pytest.raises(MissingISRCError, match=re.escape(str(_SAMPLE_TRACK["id"]))):
            _search(monkeypatch, [_raw_track(isrc="")])


class TestPreviewUnavailable:
    """Verify fail-loud behaviour when a track has no preview URL."""

    @pytest.mark.parametrize("preview", ["", None], ids=["empty_string", "null"])
    def test_preview_unavailable_raises(self, monkeypatch, preview):
        """A track without a preview URL must raise PreviewUnavailableError."""
        with pytest.raises(PreviewUnavailableError, match="audio preview unavailable"):
            _search(
                monkeypatch,
                [_raw_track(preview=preview)],
            )


class TestAlbumTolerance:
    """Verify tolerant album handling on the raw-track boundary.

    `album` is a nullable key (`NotRequired[Album | None]`), mirroring the
    persisted nullable `album` column — unlike the contract-mandated `isrc`
    and `preview`, which fail loud with domain errors, a raw track missing
    the `album` key maps to `None`.
    """

    def test_missing_album_key_maps_to_none(self, monkeypatch):
        """A raw track without an `album` key must result in `album=None`."""
        raw_no_album = cast(
            RawDeezerTrack, {k: v for k, v in _SAMPLE_TRACK.items() if k != "album"}
        )
        result = _search(monkeypatch, [raw_no_album])
        assert result[0]["album"] is None
