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
    "ArtistEnrichment",
    "DeezerTrack",
    "SongData",
    "FingerprintResponse",
]

#: The 8 collapsed DSP feature scalars (keyed by `Feature`).
FeatureScalars = dict[Feature, float]


class Artist(TypedDict):
    """Deezer artist object as it appears in an upstream track (`id`+`name`)."""

    id: int
    name: str


class ArtistEnrichment(TypedDict):
    """Result of a per-track contributor and cover art enrichment lookup."""

    artists: list[Artist]
    cover: str


class Album(TypedDict):
    """Deezer album object as it appears in an upstream track (`id`+`title`)."""

    id: int
    title: str


class DeezerTrack(TypedDict):
    """An upstream Deezer track shape (`DeezerTrack`/`confirm` payload input).

    `artists` is the canonical ordered contributor list with the main artist
    first: search matches carry a single main artist, `/track/{id}` responses
    the full `contributors` roster (main-first per Deezer). `album` may
    arrive as an object (`Album`) or, when the payload was built from
    already-normalized data, as a plain string; the fingerprint service
    flattens it on entry before persisting.

    The `album` key is always present in a validated `DeezerTrack` — a raw
    track missing `album` fails loud at the client boundary (mirroring the
    main artist). Its value may be `None`. `isrc`/`preview` are likewise
    guaranteed present and non-empty after client-side validation. `cover`
    is the display-only art URL derived from Deezer's `md5_image`;
    consumers that persist songs ignore it.
    """

    deezer_id: int
    title: str
    isrc: str
    duration: int
    preview: str
    cover: str
    artists: list[Artist]
    album: Album | str | None


class SongData(TypedDict):
    """The song fields the repository persists (`create_song_and_fingerprint`).

    Uses persistence names (`preview_url`) and carries `artists` as the
    canonical `Artist` list (main first) plus `album` as a plain string. The
    `album` key is always present; its value may be `None`. `cover` is not
    persisted (display-only), so it is absent here. The service maps from
    `DeezerTrack` to this shape.
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
