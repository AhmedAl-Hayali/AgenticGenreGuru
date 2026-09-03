"""Unit tests for `fingerprint_service` pure mapping functions.

Tests `_feature_map`, `_build_response`, `_artist_name`, `_album_title`,
and `_to_song_data` in isolation — no monkeypatch, no network. The
orchestration path is covered by the integration suite
(`tests/integration/test_fingerprint_service.py`).
"""

from typing import Any, cast

import pytest

from genreguru.audio.features import Feature
from genreguru.db.models import Song
from genreguru.dto import Album, Artist, FeatureScalars, FingerprintResponse
from genreguru.fingerprint_service import (
    _album_title,
    _artist_name,
    _build_response,
    _feature_map,
    _to_song_data,
)
from tests.factories import SongFactory, SongFingerprintFactory
from tests.repo_payloads import (
    EXPECTED_FINGERPRINT_KEYS,
    build_repo_payloads,
    match_from_song,
)


def _make_song_with_fingerprint() -> Song:
    """Build a Song with an attached SongFingerprint via factories."""
    song: Song = SongFactory.build()
    song.fingerprint = SongFingerprintFactory.build(song=song)
    return song


def _feature_scalars(song: Song) -> FeatureScalars:
    """Read the 8 float scalars off *song*'s fingerprint, mirroring `_feature_map`."""
    return {f: float(getattr(song.fingerprint, f.value)) for f in Feature}


class TestFeatureMap:
    """Verify `_feature_map` reads all 8 scalars from a Song's fingerprint."""

    def test_guard_raises_when_no_fingerprint(self):
        """`_feature_map` must raise ValueError when the song has no fingerprint."""
        song: Song = SongFactory.build()
        # `song.fingerprint` is a non-None relationship, so silence the ping by
        # casting through `Any` to force the guard's "no fingerprint" branch.
        cast(Any, song).fingerprint = None

        with pytest.raises(ValueError):
            _feature_map(song)

    def test_returns_all_features(self):
        """`_feature_map` must return a dict keyed by every `Feature` member."""
        song = _make_song_with_fingerprint()
        result = _feature_map(song)

        assert set(result.keys()) == set(Feature)

    def test_values_match_fingerprint(self):
        """Each scalar must match the underlying `SongFingerprint` attribute."""
        song = _make_song_with_fingerprint()
        result = _feature_map(song)

        for f in Feature:
            assert result[f] == _feature_scalars(song)[f]

    def test_values_are_float(self):
        """All values must be `float`, not the raw attribute type."""
        song = _make_song_with_fingerprint()
        result = _feature_map(song)

        for v in result.values():
            assert isinstance(v, float)

    def test_values_coerce_int_to_float(self):
        """`_feature_map` must coerce int-valued attrs to `float`, not pass through."""
        song = _make_song_with_fingerprint()
        # Factories emit Python floats, so the `float()` in `_feature_map`
        # would otherwise be a no-op; an int proves the coercion actually runs.
        cast(Any, song.fingerprint).spectral_centroid = 3

        result = _feature_map(song)

        assert result[Feature.SPECTRAL_CENTROID] == 3.0
        assert type(result[Feature.SPECTRAL_CENTROID]) is float

    def test_values_match_known_sample(self):
        """`_feature_map` must read the exact named attribute for each feature."""
        song = _make_song_with_fingerprint()
        # Force every scalar to a distinctive literal (distinct from each other
        # and from factory defaults) so any mis-read — e.g. swapped columns —
        # surfaces instead of silently matching the factory value.
        expected: FeatureScalars = {
            Feature.SPECTRAL_CENTROID: 1.0,
            Feature.RMS: 2.0,
            Feature.SPECTRAL_BANDWIDTH: 3.0,
            Feature.SPECTRAL_CONTRAST: 4.0,
            Feature.SPECTRAL_FLATNESS: 5.0,
            Feature.SPECTRAL_ROLLOFF: 6.0,
            Feature.ZERO_CROSSING_RATE: 7.0,
            Feature.MFCC: 8.0,
        }
        for f, value in expected.items():
            cast(Any, song.fingerprint).__setattr__(f.value, value)

        result = _feature_map(song)

        for f, value in expected.items():
            assert result[f] == value


class TestBuildResponse:
    """Verify `_build_response` assembles a `FingerprintResponse`."""

    @pytest.fixture
    def built_response(self) -> tuple[Song, FeatureScalars, FingerprintResponse]:
        """Song/features/response triad built once per test."""
        song = _make_song_with_fingerprint()
        features = _feature_scalars(song)
        return song, features, _build_response(song, features)

    def test_response_shape(self, built_response):
        """Must return a dict with exactly the four `FingerprintResponse` keys."""
        _, _, result = built_response

        assert set(result) == {"song_id", "deezer_id", "isrc", "fingerprint"}

    def test_song_fields(self, built_response):
        """`song_id`, `deezer_id`, `isrc` must mirror the Song attributes."""
        song, _, result = built_response

        assert result["song_id"] == str(song.id)
        assert result["deezer_id"] == song.deezer_id
        assert result["isrc"] == song.isrc

    def test_fingerprint_contains_all_features_and_vector_length(self, built_response):
        """`fingerprint` dict must contain all features plus `vector_length`."""
        _, _, result = built_response

        assert set(result["fingerprint"]) == EXPECTED_FINGERPRINT_KEYS
        assert result["fingerprint"]["vector_length"] == len(Feature)

    def test_feature_values_preserved(self, built_response):
        """Feature values in the response must match the input `FeatureScalars`."""
        _, features, result = built_response

        for f in Feature:
            assert result["fingerprint"][f.value] == features[f]


class TestArtistName:
    """Verify `_artist_name` flattens object-shaped artist payloads."""

    @pytest.mark.parametrize(
        ("artist", "expected"),
        [
            (Artist(id=27, name="Daft Punk"), "Daft Punk"),
            ("Daft Punk", "Daft Punk"),
        ],
    )
    def test_artist_name_flattens(self, artist, expected):
        """`_artist_name` flattens objects; plain strings pass through."""
        assert _artist_name(artist) == expected


class TestAlbumTitle:
    """Verify `_album_title` flattens object-shaped / None / string payloads."""

    @pytest.mark.parametrize(
        ("album", "expected_album"),
        [
            (Album(id=302127, title="Discovery"), "Discovery"),
            ("Discovery", "Discovery"),
            (None, None),
        ],
    )
    def test_album_title_flattens(self, album, expected_album):
        """`_album_title` flattens objects/None/strings; `None` stays `None`."""
        assert _album_title(album) is expected_album


class TestToSongData:
    """Verify `_to_song_data` maps a `DeezerTrack` to the `SongData` shape."""

    @pytest.mark.parametrize(
        ("artist", "exp_artist", "album", "exp_album"),
        [
            (
                Artist(id=27, name="Daft Punk"),
                "Daft Punk",
                Album(id=302127, title="Discovery"),
                "Discovery",
            ),
            ("Daft Punk", "Daft Punk", None, None),
        ],
    )
    def test_flattens_artist_and_album(self, artist, exp_artist, album, exp_album):
        """`_to_song_data` flattens object artist/album to strings; None maps to None."""
        song_data, *_ = build_repo_payloads()
        track = match_from_song(song_data)
        track["artist"] = artist
        track["album"] = album

        result = _to_song_data(track)

        assert result["artist"] == exp_artist
        assert result["album"] is exp_album
        assert result["deezer_id"] == song_data["deezer_id"]
        assert result["isrc"] == song_data["isrc"]
        assert result["title"] == song_data["title"]
        assert result["preview_url"] == song_data["preview_url"]
        assert result["duration"] == song_data["duration"]
