"""Integration test for SongRepository dedup-by-ISRC persistence.

Verifies that `genreguru.db.SongRepository` correctly
reuses an existing song when the ISRC already exists, and creates fresh
records for new ISRCs.

Song/SongFingerprint fixtures come from the FactoryBoy factories
(`tests/factories.py`) via `build()`; the repo-input dicts come from
`tests/repo_payloads.build_repo_payloads` so every variant is realistic and unique.

Uses the real PostgreSQL database via the shared `db_session` fixture
(SAVEPOINT isolation — no data persists).
"""

import logging
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from genreguru.audio.features import Feature
from genreguru.db.models import AudioFormat, SongFingerprint
from genreguru.db.repositories import Song, SongRepository
from tests.repo_payloads import build_repo_payloads


def _build_and_create(repo, *, include_audio_spec=True, overrides=None):
    """Build realistic payloads and create via the repository.

    Returns the created Song plus the song_data and features dicts so tests
    can assert against them. When `include_audio_spec` is False the
    `audio_format`/`sample_rate` arguments are omitted so the repository's
    own defaults are exercised. `overrides` mutates the song_data dict (e.g.
    `{"album": None}`) before creation.
    """
    if include_audio_spec:
        song_data, features, audio_format, sample_rate = build_repo_payloads()
    else:
        song_data, features, _, _ = build_repo_payloads(include_audio_spec=False)
        audio_format = sample_rate = None

    if overrides:
        song_data.update(overrides)
    if not include_audio_spec:
        return (
            repo.create_song_and_fingerprint(song_data, features),
            song_data,
            features,
        )
    return (
        repo.create_song_and_fingerprint(
            song_data, features, audio_format, sample_rate
        ),
        song_data,
        features,
    )


def _collide_on_flush(repo, monkeypatch):
    """Simulate a concurrent writer colliding on the ISRC unique constraint."""

    def colliding_flush():
        raise IntegrityError("duplicate key", {}, ValueError("duplicate key"))

    monkeypatch.setattr(repo._session, "flush", colliding_flush)


def _create_twice(repo):
    """Create a song, then create again from the same repo-input payloads.

    Returns the two Songs, simulating a genuine duplicate-ISRC insert.
    """
    song_data, features, audio_format, sample_rate = build_repo_payloads()
    first = repo.create_song_and_fingerprint(
        song_data, features, audio_format, sample_rate
    )
    second = repo.create_song_and_fingerprint(
        song_data, features, audio_format, sample_rate
    )
    return first, second


class TestCreateSongAndFingerprint:
    """Verify `create_song_and_fingerprint` persists both Song and SongFingerprint rows."""

    def test_creates_song_row(self, repo: SongRepository):
        """Song row must be inserted with a generated ID and correct ISRC."""
        song, song_data, _ = _build_and_create(repo)
        assert song.id is not None
        assert song.isrc == song_data["isrc"]
        assert song.deezer_id == song_data["deezer_id"]

    def test_creates_fingerprint_with_all_features(
        self, db_session, repo: SongRepository
    ):
        """SongFingerprint row must be linked and store all 8 features with full precision."""
        song, _, features = _build_and_create(repo)
        fp = SongFingerprint.latest_for_song(db_session, song.id)
        assert fp is not None
        assert fp.song_id == song.id
        for f in Feature:
            assert getattr(fp, f.value) == pytest.approx(features[f])

    def test_default_audio_format_and_sample_rate(
        self, db_session, repo: SongRepository
    ):
        """Omitted `audio_format`/`sample_rate` must fall back to MP3/22050."""
        song, _, _ = _build_and_create(repo, include_audio_spec=False)
        fp = SongFingerprint.latest_for_song(db_session, song.id)
        assert fp is not None
        assert fp.audio_format == AudioFormat.MP3
        assert fp.sample_rate == 22050

    def test_album_none_persisted(self, db_session, repo: SongRepository):
        """A missing album must persist as NULL."""
        song, _, _ = _build_and_create(repo, overrides={"album": None})
        assert song.album is None


class TestDedupByISRC:
    """Verify that duplicate ISRCs reuse the existing song instead of creating new rows."""

    def test_same_isrc_returns_existing_song(self, repo: SongRepository):
        """Second insert with the same ISRC must return the original song."""
        first, second = _create_twice(repo)
        assert first.id == second.id

    def test_same_isrc_no_duplicate_fingerprint(self, db_session, repo: SongRepository):
        """Dedup must not create a second SongFingerprint for the same ISRC."""
        _, second = _create_twice(repo)
        fp = SongFingerprint.latest_for_song(db_session, second.id)
        assert fp is not None
        count = (
            db_session.query(SongFingerprint)
            .filter(SongFingerprint.song_id == second.id)
            .count()
        )
        assert count == 1

    def test_different_isrc_creates_new_song(self, repo: SongRepository):
        """Distinct ISRCs must produce distinct Song rows."""
        first, song_data_1, _ = _build_and_create(repo)
        second, song_data_2, _ = _build_and_create(repo)
        assert first.id != second.id
        assert first.isrc == song_data_1["isrc"]
        assert second.isrc == song_data_2["isrc"]

    def test_concurrent_duplicate_isrc_logs_warning_and_returns_existing(
        self, repo: SongRepository, monkeypatch, caplog
    ):
        """A unique-violation insert must log WARNING and return the existing song."""
        # Stand-in for the song already committed by a concurrent writer. Its
        # id is never persisted here — it is returned by the mocked re-fetch
        # and compared only in-memory — so the UUID variant is irrelevant.
        concurrent = SimpleNamespace(id=uuid.uuid7())

        # Miss on the dedup pre-check (the TOCTOU race), then hit on the
        # post-savepoint re-fetch which resolves to the concurrent song.
        results = iter([None, concurrent])
        monkeypatch.setattr(
            Song,
            "find_by_isrc",
            lambda _session, _isrc: next(results),
        )

        _collide_on_flush(repo, monkeypatch)

        with caplog.at_level(logging.WARNING, logger="genreguru.db.repositories"):
            result, _, _ = _build_and_create(repo)

        assert result.id == concurrent.id
        assert "concurrent duplicate isrc" in caplog.text

    def test_concurrent_insert_second_fetch_missing_raises_integrity_error(
        self, repo: SongRepository, monkeypatch
    ):
        """If the post-rollback re-fetch also misses the concurrent song, IntegrityError propagates."""
        monkeypatch.setattr(
            Song,
            "find_by_isrc",
            lambda _session, _isrc: None,
        )

        _collide_on_flush(repo, monkeypatch)

        with pytest.raises(IntegrityError):
            _build_and_create(repo)


class TestFindByISRC:
    """Verify `SongRepository.find_by_isrc` and its hit/miss logging."""

    def test_existing_isrc_returns_song(self, repo: SongRepository, caplog):
        """Must return the song matching the given ISRC and log a hit."""
        created, _, _ = _build_and_create(repo)
        isrc = created.isrc
        with caplog.at_level(logging.INFO, logger="genreguru.db.repositories"):
            found = repo.find_by_isrc(isrc)
        assert found is not None
        assert found.id == created.id
        assert f"isrc lookup hit isrc={isrc}" in caplog.text

    def test_nonexistent_isrc_returns_none(self, repo: SongRepository, caplog):
        """Must return None for an ISRC not present in the database and log a miss."""
        with caplog.at_level(logging.INFO, logger="genreguru.db.repositories"):
            found = repo.find_by_isrc("NOSUCH0000000")
        assert found is None
        assert "isrc lookup miss isrc=NOSUCH0000000" in caplog.text
