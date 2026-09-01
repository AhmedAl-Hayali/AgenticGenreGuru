"""Shared test-data builders for repository / fingerprint-service tests.

Centralizes repo-input construction so a schema or `Feature` change needs
updating in exactly one place. Both integration test modules import from
here instead of re-declaring payload helpers.
"""

from typing import Literal, cast, overload

from genreguru.audio.features import Feature
from genreguru.db.models import AudioFormat, Song, SongFingerprint
from genreguru.dto import FeatureScalars, SongData
from tests.factories import SongFactory, SongFingerprintFactory

_SONG_KEYS = (
    "deezer_id",
    "isrc",
    "title",
    "artist",
    "album",
    "preview_url",
    "duration",
)


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

    When `include_audio_spec` is False, `audio_format`/`sample_rate` are
    None so the repository's defaults are exercised.
    """
    song: Song = SongFactory.build()
    fp: SongFingerprint = SongFingerprintFactory.build(song=song)

    song_data: SongData = cast(SongData, {k: getattr(song, k) for k in _SONG_KEYS})
    features: FeatureScalars = {f: getattr(fp, f.value) for f in Feature}
    audio_format = AudioFormat(fp.audio_format) if include_audio_spec else None
    sample_rate = fp.sample_rate if include_audio_spec else None

    return song_data, features, audio_format, sample_rate
