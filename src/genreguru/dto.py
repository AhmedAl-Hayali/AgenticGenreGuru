"""Data-transfer shapes passed across layer boundaries (service, repo, tests).

TypedDict (not dataclass) because these flow as plain dicts across layer
boundaries: the service response is serialized directly by Django's
`JsonResponse`, and the repository indexes `song_data` by string key.

Only shapes that genuinely cross an abstraction boundary live here. Purely
module-local staging types belong in the module that consumes them (e.g.
the fingerprint-service normalization bridge), not in this shared file.

`Feature` remains authoritative in its domain module
(`genreguru/audio/features.py`) and is referenced here, not re-defined.
"""

from typing import TypedDict

from genreguru.audio.features import Feature

__all__ = [
    "FeatureScalars",
    "Artist",
    "Album",
    "SongData",
]

#: The 8 collapsed DSP feature scalars (keyed by `Feature`).
FeatureScalars = dict[Feature, float]


class Artist(TypedDict):
    """Deezer artist object as it appears in an upstream track (`id`+`name`)."""

    id: int
    name: str


class Album(TypedDict):
    """Deezer album object as it appears in an upstream track (`id`+`title`)."""

    id: int
    title: str


class SongData(TypedDict):
    """The song fields the repository persists (`create_song_and_fingerprint`).

    Uses persistence names (`preview_url`) and always carries `artist`/`album`
    as plain strings. The service maps from `DeezerTrack` to this shape.
    """

    deezer_id: int
    isrc: str
    title: str
    artist: str
    album: str | None
    preview_url: str
    duration: int
