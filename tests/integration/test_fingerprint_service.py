"""Integration test for `FingerprintService.process_fingerprint` logging.

Verifies the reuse/fresh outcome is emitted via `log_fingerprint_outcome`
with the `reused=true/false` context field (T025 contract): a prior ISRC
match returns the stored song (`reused=true`), a fresh ISRC fetches,
extracts, and stores (`reused=false`).

Both paths run against the real PostgreSQL via the shared `db_session`
fixture (SAVEPOINT isolation — no data persists).
"""

import logging
from typing import Protocol, cast

import numpy as np

from genreguru.audio.features import Feature
from genreguru.db.models import SongFingerprint
from genreguru.db.repositories import SongRepository
from genreguru.dto import DeezerTrack
from genreguru.fingerprint_service import process_fingerprint
from tests.repo_payloads import (
    EXPECTED_FINGERPRINT_KEYS,
    build_repo_payloads,
    match_from_song,
)

_SR = 44100
_SAMPLE_LENGTH_SEC = 0.5
_MOD = "genreguru.fingerprint_service"


class _FingerprintLogRecord(Protocol):
    reused: bool
    isrc: str


def _stub_audio(monkeypatch):
    """Replace the fetch/extract/collapse pipeline with deterministic fakes.

    A non-default sample rate (44100) proves sr is threaded end-to-end
    through `process_fingerprint` into the persisted fingerprint. Returns a
    counter callable that reports how many times `fetch_snippet` was invoked
    since this stub was installed.
    """
    n_calls = 0

    def fake_fetch(_url: str) -> bytes:
        nonlocal n_calls

        n_calls += 1
        return b"\x00" * 1024

    def fake_load(_bytes, **_kwargs):
        return np.zeros(int(_SR * _SAMPLE_LENGTH_SEC)), _SR

    def fake_extract(_mono, _sr):
        return {f: np.array([1.0]) for f in Feature}

    def fake_collapse(features):
        return {f: float(arr.mean()) for f, arr in features.items()}

    monkeypatch.setattr(f"{_MOD}.fetch_snippet", fake_fetch)
    monkeypatch.setattr(f"{_MOD}.load_audio", fake_load)
    monkeypatch.setattr(f"{_MOD}.extract_features", fake_extract)
    monkeypatch.setattr(f"{_MOD}.collapse_features", fake_collapse)

    def fetch_calls() -> int:
        return n_calls

    return fetch_calls


def _build_track(song_data, *, artist, album) -> DeezerTrack:
    """Build a ``DeezerTrack`` from repo payloads with the given artist/album.

    Delegates to ``match_from_song`` for the field mapping and overrides
    ``artist``/``album`` so each caller controls the shape.
    """
    track = match_from_song(song_data)
    track["artist"] = artist
    track["album"] = album
    return track


def _single_service_record(caplog):
    """Return the single log record captured from the fingerprint_service logger.

    Filters ``caplog.records`` by ``_MOD`` name. Asserts exactly one
    record exists.
    """
    records: list[logging.LogRecord] = [r for r in caplog.records if r.name == _MOD]
    assert records, "no fingerprint_service log record captured"
    assert len(records) == 1, f"expected 1 log record, got {len(records)}"
    return cast(_FingerprintLogRecord, records[0])


class TestReusePath:
    """Verify the reuse path: prior ISRC match returns stored song, logs `reused=true`."""

    def test_reuse_path_returns_existing_and_logs_reused_true(
        self, db_session, repo: SongRepository, monkeypatch, caplog
    ):
        """A prior ISRC match must return the stored song and log `reused=true`."""
        song_data, features, audio_format, sample_rate = build_repo_payloads()
        existing = repo.create_song_and_fingerprint(
            song_data, features, audio_format, sample_rate
        )
        fetch_calls = _stub_audio(monkeypatch)

        with caplog.at_level(logging.INFO, logger=_MOD):
            result = process_fingerprint(db_session, match_from_song(song_data), repo)

        record = _single_service_record(caplog)
        assert result["song_id"] == str(existing.id)
        assert result["deezer_id"] == song_data["deezer_id"]
        assert result["fingerprint"]["vector_length"] == len(Feature)
        assert fetch_calls() == 0

        assert record.reused is True
        assert record.isrc == song_data["isrc"]

        # End-to-end signal that the reuse path returns a complete fingerprint
        # (keys/vector_length defined at unit altitude via the shared constant).
        assert set(result["fingerprint"]) == EXPECTED_FINGERPRINT_KEYS


class TestFreshPath:
    """Verify the fresh path: new ISRC fetches, extracts, stores, logs `reused=false`."""

    def test_fresh_path_returns_new_song_and_logs_reused_false(
        self, db_session, repo: SongRepository, monkeypatch, caplog
    ):
        """A fresh ISRC must fetch, extract, store, and log `reused=false`."""
        song_data, *_ = build_repo_payloads()
        fetch_calls = _stub_audio(monkeypatch)

        with caplog.at_level(logging.INFO, logger=_MOD):
            result = process_fingerprint(db_session, match_from_song(song_data), repo)

        record = _single_service_record(caplog)
        stored = repo.find_by_isrc(song_data["isrc"])
        assert stored is not None

        assert result["song_id"] == str(stored.id)
        assert result["deezer_id"] == song_data["deezer_id"]
        assert result["fingerprint"]["vector_length"] == len(Feature)
        assert result["fingerprint"][Feature.SPECTRAL_CENTROID] == 1.0
        assert fetch_calls() > 0

        assert record.reused is False
        assert record.isrc == song_data["isrc"]

        # End-to-end signal that the fresh path returns a complete fingerprint
        # (keys/vector_length defined at unit altitude via the shared constant).
        assert set(result["fingerprint"]) == EXPECTED_FINGERPRINT_KEYS

        fp = SongFingerprint.latest_for_song(db_session, stored.id)
        assert fp is not None
        assert fp.sample_rate == _SR


class TestFlattening:
    """Verify artist/album flattening from upstream Deezer payload shapes."""

    def test_fresh_path_flattens_raw_artist_and_album(
        self, db_session, repo: SongRepository, monkeypatch
    ):
        """Raw object-shaped artist/album must flatten to strings (upstream Deezer payload)."""
        song_data, *_ = build_repo_payloads()
        fetch_calls = _stub_audio(monkeypatch)

        result = process_fingerprint(
            db_session,
            _build_track(
                song_data,
                artist={"id": 27, "name": "Daft Punk"},
                album={"id": 302127, "title": "Discovery"},
            ),
            repo,
        )

        stored = repo.find_by_isrc(song_data["isrc"])
        assert stored is not None
        assert stored.artist == "Daft Punk"
        assert stored.album == "Discovery"

        assert result["song_id"] == str(stored.id)
        # Smoke-signal that the full fresh pipeline ran: the stub yields 1.0
        # for every feature, so one probe verifies fetch → extract → response.
        assert result["fingerprint"][Feature.SPECTRAL_CENTROID] == 1.0
        assert fetch_calls() > 0

    def test_fresh_path_album_none_flattens(
        self, db_session, repo: SongRepository, monkeypatch
    ):
        """A DeezerTrack with album=None must persist NULL through orchestration."""
        song_data, *_ = build_repo_payloads()
        fetch_calls = _stub_audio(monkeypatch)

        result = process_fingerprint(
            db_session,
            _build_track(song_data, artist="Daft Punk", album=None),
            repo,
        )

        stored = repo.find_by_isrc(song_data["isrc"])
        assert stored is not None
        assert stored.album is None

        assert result["song_id"] == str(stored.id)
        # Smoke-signal that the full fresh pipeline ran (see prior test).
        assert result["fingerprint"][Feature.SPECTRAL_CENTROID] == 1.0
        assert fetch_calls() > 0
