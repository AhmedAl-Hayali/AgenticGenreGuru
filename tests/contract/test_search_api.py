"""Contract tests for GET /api/search/ endpoint.

Validates the JSON response shape, status codes (200/404/503), the real
`[:5]` cap, and that error paths create NO partial Song/SongFingerprint rows.

GREEN phase: `search_view` is exercised as the REAL view. The only mocked
dependency is `DeezerClient.search` (the network boundary — it already
returns enrichments: full roster + sanitized wire shape), so the view's own
logic — empty-query 404, error-code mapping, 5-match cap, `matches=[]` for
zero results — is genuinely under test.

The module-local route resolution is skipped: tests run against the real
`genreguru_web.urls` → `fingerprint_app.urls` routing via the default
`ROOT_URLCONF`, so a regression in URL wiring is caught.

`no_partial_rows` tests assert against PostgreSQL via `db_session`; the
`db_schema` fixture creates the `songs`/`song_fingerprints` tables once.
"""

from typing import cast

import pytest

from genreguru.db.models import Song, SongFingerprint
from genreguru.deezer import client as deezer_client
from genreguru.dto import Album, Track
from genreguru.errors import (
    MissingISRCError,
    NetworkDisconnectedError,
    PreviewUnavailableError,
    TrackNotFoundError,
)
from tests.sample_payloads import DEEZER_MATCH, DEEZER_MATCHES, error_of


def matches_of(resp) -> list[Track]:
    """Return the typed `matches` array of a search response."""
    body = resp.json()
    assert isinstance(body, dict) and isinstance(body.get("matches"), list)
    return body["matches"]


@pytest.fixture
def get_search(django_client, monkeypatch):
    """GET /api/search/ with a stubbed `DeezerClient.search`; returns the response.

    `query` is the search term to issue (required, keyword-only), `result`
    sets the returned matches (default empty), and `error` makes the search
    stub raise.
    """

    def _search(
        *,
        query: str,
        result: list[Track] | None = None,
        error: BaseException | None = None,
    ):
        def fake_search(self, q: str) -> list[Track]:
            if error is not None:
                raise error
            return list(result or [])

        monkeypatch.setattr(deezer_client.DeezerClient, "search", fake_search)
        return django_client.get(f"/api/search/?query={query}")

    return _search


class TestSearchResponseShape:
    """Verify 200 response JSON shape for a successful search."""

    def test_success_response_shape(self, get_search):
        """A successful search must return 200 with `status` `success` and a list."""
        resp = get_search(query="Daft+Punk", result=DEEZER_MATCHES)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert isinstance(matches_of(resp), list)

    def test_match_shape_contract(self, get_search):
        """Each match must carry the full `SEARCH_FIELDS` shape with real values."""
        match = matches_of(get_search(query="Daft+Punk", result=DEEZER_MATCHES))[0]
        assert set(deezer_client.SEARCH_FIELDS) <= set(match)
        artists = match["artists"]
        assert artists and "id" in artists[0] and "name" in artists[0]
        cover = match["cover"]
        assert cover.startswith("https://cdn-images.dzcdn.net/images/cover/")
        assert cover.endswith("/300x300.jpg")
        album = cast(Album, match["album"])
        assert "id" in album
        assert "title" in album

    def test_five_matches(self, get_search):
        """Response must cap the matches list at 5 entries (real `[:5]`)."""
        resp = get_search(query="Daft+Punk", result=[DEEZER_MATCH] * 10)
        assert resp.json()["status"] == "success"
        assert len(matches_of(resp)) == 5

    def test_zero_results_returns_200_empty(self, get_search):
        """Zero Deezer matches must return 200 with an empty matches list."""
        resp = get_search(query="Daft+Punk", result=[])
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert matches_of(resp) == []


class TestSearch404:
    """Verify 404 response and no partial DB rows on empty query / track-not-found."""

    def test_404_empty_query(self, get_search):
        """An empty/whitespace query is a client error → HTTP 404."""
        resp = get_search(query="")
        assert resp.status_code == 404
        assert resp.json()["status"] == "error"
        assert error_of(resp) == "TrackNotFoundError"

    def test_404_track_not_found(self, get_search):
        """`TrackNotFoundError` from the dependency must produce HTTP 404."""
        resp = get_search(query="Daft+Punk", error=TrackNotFoundError("no match"))
        assert resp.status_code == 404
        assert resp.json()["status"] == "error"
        assert error_of(resp) == "TrackNotFoundError"


class TestNoPartialRowsOnError:
    """Verify error paths create NO Song/SongFingerprint rows."""

    @pytest.mark.parametrize(
        "error",
        [
            TrackNotFoundError("no match"),
            NetworkDisconnectedError("network broke"),
        ],
        ids=["track_not_found_404", "network_503"],
    )
    def test_error_creates_no_partial_rows(
        self, db_schema, db_session, get_search, error
    ):
        """An error from the dependency must not create any Song/SongFingerprint rows.

        Asserts a zero **delta** (count before vs after) rather than an empty
        table, so pre-existing committed rows in the shared dev database (e.g.
        from the live confirm flow) cannot mask a partial-row leak.
        """
        songs_before = db_session.query(Song).count()
        fingerprints_before = db_session.query(SongFingerprint).count()

        get_search(query="Daft+Punk", error=error)

        assert db_session.query(Song).count() == songs_before
        assert db_session.query(SongFingerprint).count() == fingerprints_before


class TestSearch503:
    """Verify 503 response on network failure."""

    def test_503_body_shape(self, get_search):
        """NetworkDisconnectedError must produce HTTP 503 with error status."""
        resp = get_search(
            query="Daft+Punk", error=NetworkDisconnectedError("network broke")
        )
        assert resp.status_code == 503
        assert resp.json()["status"] == "error"
        assert "NetworkDisconnectedError" in error_of(resp)


class TestSearch500:
    """Verify 500 responses on upstream data-integrity failures."""

    @pytest.mark.parametrize(
        "error",
        [MissingISRCError("missing isrc"), PreviewUnavailableError("no preview")],
        ids=["missing_isrc", "preview_unavailable"],
    )
    def test_500_integrity_failure_maps_internal(self, get_search, error):
        """A data-integrity failure from the dependency must map to HTTP 500."""
        resp = get_search(query="Daft+Punk", error=error)
        assert resp.status_code == 500
        assert resp.json()["status"] == "error"
        assert "internal server error" in error_of(resp)


class TestSearchMethodEnforcement:
    """Verify GET-only enforcement on the search endpoint."""

    def test_post_is_rejected(self, django_client):
        """A POST to /api/search/ must be rejected with HTTP 405."""
        resp = django_client.post("/api/search/?query=Daft+Punk")
        assert resp.status_code == 405
