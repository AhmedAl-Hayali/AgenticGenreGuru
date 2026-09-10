"""Shared test-data builders for repository / fingerprint-service tests.

Centralizes repo-input construction so a schema or `Feature` change needs
updating in exactly one place. Both integration test modules import from
here instead of re-declaring payload helpers.
"""

from typing import Literal, cast, overload

from genreguru.audio.features import Feature
from genreguru.db.models import AudioFormat, Song, SongFingerprint
from genreguru.dto import Album, Artist, ConfirmTrack, FeatureScalars, SongData
from tests.factories import SongArtistFactory, SongFactory, SongFingerprintFactory

# `SongData` keys whose value is read straight off the `Song` model — everything
# except `artists`, which is relationship-projected (see `build_repo_payloads`).
_SONG_SCALAR_KEYS = tuple(k for k in SongData.__annotations__ if k != "artists")

# All `Feature` values plus the synthetic `vector_length` key that compose a
# fingerprint response. Single source of truth so a `Feature` change needs
# updating here only.
EXPECTED_FINGERPRINT_KEYS = {f.value for f in Feature} | {"vector_length"}


@overload
def build_repo_payloads(
    *,
    include_audio_spec: Literal[True] = True,
) -> tuple[SongData, FeatureScalars, AudioFormat, int]: ...


@overload
def build_repo_payloads(
    *,
    include_audio_spec: Literal[False],
) -> tuple[SongData, FeatureScalars, None, None]: ...


def build_repo_payloads(
    *,
    include_audio_spec: bool = True,
) -> tuple[SongData, FeatureScalars, AudioFormat | None, int | None]:
    """Build repo-input song/feature dicts from the model factories.

    Contributors are synthetic and arbitrary by design (canonical payloads
    live with the mapping/contract suites). `include_audio_spec=False` yields
    `None` audio fields to exercise repository defaults.
    """
    song: Song = SongFactory.build()
    fp: SongFingerprint = SongFingerprintFactory.build(song=song)
    contributors = SongArtistFactory.build_contributors(song, count=1)

    song_data: SongData = cast(
        SongData, {k: getattr(song, k) for k in _SONG_SCALAR_KEYS}
    )
    song_data["artists"] = [
        SongArtistFactory.to_artist(contributor) for contributor in contributors
    ]
    features: FeatureScalars = {f: getattr(fp, f.value) for f in Feature}
    audio_format = fp.audio_format if include_audio_spec else None
    sample_rate = fp.sample_rate if include_audio_spec else None

    return song_data, features, audio_format, sample_rate


def match_from_song(
    song_data: SongData,
    *,
    artists: list[Artist] | None = None,
    album: Album | None = None,
) -> ConfirmTrack:
    """Shape a `ConfirmTrack` input for `process_fingerprint` from repo `song_data`.

    Field names are swapped to the Deezer contract (`preview`, not
    `preview_url`); the canonical main-first `artists` list carries through
    unchanged unless overridden.

    The override surface is principled: `artists` and `album` are the only two
    `ConfirmTrack` fields `SongData` cannot produce faithfully. The persisted
    `Song.album` holds only a flattened title string, so the `Album` object
    (esp. its id) is never reconstructable from repo state and the confirm
    shape defaults to `album=None`; every other field is a 1:1 copy. Pass a
    real `Album` via `album=` and a full `list[Artist]` via `artists=` when
    those object shapes must reach `process_fingerprint`.
    """
    return {
        "deezer_id": song_data["deezer_id"],
        "title": song_data["title"],
        "isrc": song_data["isrc"],
        "duration": song_data["duration"],
        "preview": song_data["preview_url"],
        "artists": artists if artists is not None else song_data["artists"],
        "album": album,
    }
