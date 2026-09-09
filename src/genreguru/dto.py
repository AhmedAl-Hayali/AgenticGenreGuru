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
    "Track",
    "SongData",
    "FingerprintResponse",
]

FeatureScalars = dict[Feature, float]


class Artist(TypedDict):
    """Deezer artist object as it appears in an upstream track (`id`+`name`)."""

    id: int
    name: str


class Album(TypedDict):
    """Deezer album object as it appears in an upstream track (`id`+`title`)."""

    id: int
    title: str


class Track(TypedDict):
    """The normalized GenreGuru track — what the client returns and the search wire.

    NOT the raw upstream object (see `RawDeezerTrack`): `deezer_id` renames
    Deezer's `id`, `artists` is the canonical ordered contributor list with
    the main artist first (a single main artist on search matches, the full
    `contributors` roster on `/track/{id}`), and `cover` is derived from
    `md5_image`. `album` is the Deezer album object; its key is always
    present in a validated track and its value may be `None`. `isrc`/`preview`
    are guaranteed present and non-empty after client-side validation.
    `cover` is display-only, always present on search matches, and never part
    of the confirm payload (see `ConfirmTrack`).
    """

    deezer_id: int
    title: str
    isrc: str
    duration: int
    preview: str
    artists: list[Artist]
    album: Album | None
    cover: str


class SongData(TypedDict):
    """The song fields the repository persists (`create_song_and_fingerprint`).

    Uses persistence names (`preview_url`) and carries `artists` as the
    canonical `Artist` list (main first) plus `album` as a plain string. The
    `album` key is always present; its value may be `None`. `cover` is not
    persisted (display-only), so it is absent here. The service maps from
    `Track` to this shape.
    """

    deezer_id: int
    isrc: str
    title: str
    artists: list[Artist]
    album: str | None
    preview_url: str
    duration: int


class FingerprintResponse(TypedDict):
    """The serialized fingerprint sent back to the client (`JsonResponse`).

    `fingerprint` holds the 8 collapsed `FeatureScalars` (snake_case keys)
    plus `vector_length` (== `len(Feature)`).
    """

    song_id: str
    deezer_id: int
    isrc: str
    fingerprint: dict[str, float | int]
