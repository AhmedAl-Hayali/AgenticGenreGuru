"""Contract tests for GET /api/search/ endpoint.

Validates the JSON response shape, status codes (200/404/503), the real
`[:5]` cap, and that error paths create NO partial Song/SongFingerprint rows.

GREEN phase: `search_view` is exercised as the REAL view. The only mocked
dependency is `DeezerSearchClient.search` (the network boundary), so
the view's own logic — empty-query 404, error-code mapping, 5-match cap,
`matches=[]` for zero results — is genuinely under test.

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
from genreguru.dto import Album, Artist, DeezerTrack
from genreguru.errors import NetworkDisconnectedError, TrackNotFoundError
from tests.sample_payloads import DEEZER_MATCH, DEEZER_MATCHES


def matches_of(resp) -> list[DeezerTrack]:
    """Return the typed `matches` array of a search response."""
    body = resp.json()
    assert isinstance(body, dict) and isinstance(body.get("matches"), list)
    return body["matches"]


def error_of(resp) -> str:
    """Return the typed `error` field of an error search response."""
    body = resp.json()
    assert isinstance(body, dict) and isinstance(body.get("error"), str)
    return body["error"]


@pytest.fixture
def get_search(django_client, monkeypatch):
    """GET /api/search/ with a stubbed `DeezerSearchClient.search`; returns the response.

    `query` is the search term to issue (required, keyword-only), `result`
    sets the returned matches (default empty), and `error` makes the stub
    raise.
    """

    def _search(
        *,
        query: str,
        result: list[DeezerTrack] | None = None,
        error: BaseException | None = None,
    ):
        def fake_search(self, q: str) -> list[DeezerTrack]:
            if error is not None:
                raise error
            return list(result or [])

        monkeypatch.setattr(deezer_client.DeezerSearchClient, "search", fake_search)
        return django_client.get(f"/api/search/?query={query}")

    return _search


class TestSearchResponseShape:
    """Verify 200 response JSON shape for a successful search."""

    def test_status_success(self, get_search):
        """Successful search must return HTTP 200 with `status` = `success`."""
        resp = get_search(query="Daft+Punk", result=DEEZER_MATCHES)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_matches_is_list(self, get_search):
        """`matches` must be a JSON array."""
        resp = get_search(query="Daft+Punk", result=DEEZER_MATCHES)
        assert isinstance(matches_of(resp), list)

    def test_match_has_required_fields(self, get_search):
        """Each match must include deezer_id, title, isrc, duration, preview, artist, album."""
        resp = get_search(query="Daft+Punk", result=DEEZER_MATCHES)
        match = matches_of(resp)[0]
        for field in [
            "deezer_id",
            "title",
            "isrc",
            "duration",
            "preview",
            "artist",
            "album",
        ]:  # Could be DEEZER_MATCH instead, but this is explicit
            assert field in match

    def test_artist_has_id_and_name(self, get_search):
        """Artist sub-object must contain `id` and `name`."""
        resp = get_search(query="Daft+Punk", result=DEEZER_MATCHES)
        artist = cast(Artist, matches_of(resp)[0]["artist"])
        assert "id" in artist
        assert "name" in artist

    def test_album_has_id_and_title(self, get_search):
        """Album sub-object must contain `id` and `title`."""
        resp = get_search(query="Daft+Punk", result=DEEZER_MATCHES)
        album = cast(Album, matches_of(resp)[0]["album"])
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
        assert "TrackNotFoundError" in error_of(resp)

    def test_404_no_partial_rows(self, db_schema, db_session, get_search):
        """TrackNotFoundError must not create any Song or SongFingerprint rows."""
        get_search(query="Daft+Punk", error=TrackNotFoundError("no match"))
        assert db_session.query(Song).count() == 0
        assert db_session.query(SongFingerprint).count() == 0


class TestSearch503:
    """Verify 503 response and no partial DB rows on network failure."""

    def test_503_body_shape(self, get_search):
        """NetworkDisconnectedError must produce HTTP 503 with error status."""
        resp = get_search(
            query="Daft+Punk", error=NetworkDisconnectedError("network broke")
        )
        assert resp.status_code == 503
        assert resp.json()["status"] == "error"
        assert "NetworkDisconnectedError" in error_of(resp)

    def test_503_no_partial_rows(self, db_schema, db_session, get_search):
        """NetworkDisconnectedError must not create any Song or SongFingerprint rows."""
        get_search(query="Daft+Punk", error=NetworkDisconnectedError("network broke"))
        assert db_session.query(Song).count() == 0
        assert db_session.query(SongFingerprint).count() == 0
