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

from typing import NotRequired, TypedDict

from genreguru.audio.features import Feature

__all__ = [
    "FeatureScalars",
    "Artist",
    "Album",
    "RawDeezerTrack",
    "DeezerSearchResponse",
    "Track",
    "ConfirmTrack",
    "DeezerError",
    "DeezerErrorEnvelope",
    "SongData",
    "FingerprintResponse",
]

# The 8 collapsed DSP feature scalars (keyed by `Feature`).
FeatureScalars = dict[Feature, float]


class Artist(TypedDict):
    """Deezer artist object as it appears in an upstream track (`id`+`name`)."""

    id: int
    name: str


class Album(TypedDict):
    """Deezer album object as it appears in an upstream track (`id`+`title`)."""

    id: int
    title: str


class RawDeezerTrack(TypedDict):
    """The upstream Deezer Track object (`contracts/deezer-api.md` §1), unnormalized.

    Raw names and shapes only — `id` (→ `deezer_id`), `artist`/`contributors`
    (→ the canonical `artists` list), `md5_image` (→ the derived `cover`).

    The strictly required keys are `id`/`title`/`duration` (structural) plus
    `isrc` and `preview`, which the contracts mandate the wire always carries:
    a violated `isrc`/`preview` fails loud with `MissingISRCError` /
    `PreviewUnavailableError` (see `_validate_track`). Everything else is a
    tolerant `.get()`-read key: `album` may be `None` or absent and maps to
    `None` (mirroring the nullable persisted `album` column), and
    `md5_image`/`artist`/`contributors` degrade gracefully.
    """

    id: int
    title: str
    duration: int
    isrc: str
    preview: str
    album: NotRequired[Album | None]
    md5_image: NotRequired[str | None]
    artist: NotRequired[Artist | None]
    contributors: NotRequired[list[Artist] | None]


class DeezerSearchResponse(TypedDict):
    """The Deezer `/search` JSON body envelope — not a track itself.

    `data` holds the raw track objects and `total` the reported result count.
    Both are tolerant (`NotRequired`) because the client reads them via
    `.get` and a `DATA_NOT_FOUND` (800) response has no track payload.
    """

    data: NotRequired[list[RawDeezerTrack]]
    total: NotRequired[int]


class DeezerError(TypedDict):
    """The Deezer error sub-object embedded in an error-envelope/body.

    The JSON layer stays untyped at runtime; this DTO is a claim about the
    upstream shape, so every key is `NotRequired` and `code` may be absent.
    """

    type: NotRequired[str]
    message: NotRequired[str]
    code: NotRequired[int | None]


class DeezerErrorEnvelope(TypedDict):
    """A Deezer JSON body carrying an embedded `error` sub-object.

    Covers both the documented error envelope and a 200 body embedding an
    error (e.g. `DATA_NOT_FOUND`). The client reads only `error.code`.
    """

    error: NotRequired[DeezerError]


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


class ConfirmTrack(TypedDict):
    """The confirmed selection a client posts to `/api/confirm/` (7 fields).

    Exactly `Track` minus the display-only `cover`: the backend rejects any
    body whose keys aren't exactly this set (missing field or extra key such
    as `cover` → 400). `album` is the Deezer album object or `None`; the
    service flattens it to the persisted title via `_album_title`.
    """

    deezer_id: int
    title: str
    isrc: str
    duration: int
    preview: str
    artists: list[Artist]
    album: Album | None


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
