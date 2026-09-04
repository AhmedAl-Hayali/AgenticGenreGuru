"""FingerprintService orchestration.

ISRC reuse path short-circuits; else fetch -> extract -> store.
Logs `reused=true/false` via the LoggerAdapter.

Exception handling is the caller's responsibility (see `confirm_view`);
this module only emits structured INFO records for the reuse/fresh outcome.
"""

import logging
from typing import cast

from sqlalchemy.orm import Session

from genreguru.audio.feature_collapse import collapse_features
from genreguru.audio.feature_extract import extract_features
from genreguru.audio.features import Feature
from genreguru.audio.loader import load_audio
from genreguru.db.models import AudioFormat, Song
from genreguru.db.repositories import SongRepository
from genreguru.deezer.snippets import fetch_snippet
from genreguru.dto import (
    Album,
    Artist,
    DeezerTrack,
    FeatureScalars,
    FingerprintResponse,
    SongData,
)
from genreguru.gglogging import log_fingerprint_outcome, timer

logger = logging.getLogger(__name__)


def _artist_name(artist: Artist | str) -> str:
    """Return the artist's `name` if it is an object, else the string."""
    return artist["name"] if isinstance(artist, dict) else cast(str, artist)


def _album_title(album: Album | str | None) -> str | None:
    """Return the album's `title` if it is an object, else the string."""
    if album is None:
        return None
    return album["title"] if isinstance(album, dict) else cast(str, album)


def _to_song_data(track: DeezerTrack) -> SongData:
    """Map an upstream `DeezerTrack` into the repo's `SongData` shape.

    Flattens `artist`/`album` from objects (`Artist`/`Album`) to plain
    strings and renames `preview` to the persistence field `preview_url`,
    all in one pass.
    """
    return {
        "deezer_id": track["deezer_id"],
        "isrc": track["isrc"],
        "title": track["title"],
        "artist": _artist_name(track["artist"]),
        "album": _album_title(track["album"]),
        "preview_url": track["preview"],
        "duration": track["duration"],
    }


def _feature_map(song: Song) -> FeatureScalars:
    """Read the 8 collapsed feature scalars off *song*'s stored fingerprint.

    Raises:
        ValueError: If *song* has no fingerprint (e.g. corrupted state).
    """
    if song.fingerprint is None:
        raise ValueError(f"song {song.id} has no fingerprint")
    return {f: float(getattr(song.fingerprint, f.value)) for f in Feature}


def _build_response(song: Song, feature_map: FeatureScalars) -> FingerprintResponse:
    """Build the fingerprint API response for *song* and *feature_map*."""
    return {
        "song_id": str(song.id),
        "deezer_id": song.deezer_id,
        "isrc": song.isrc,
        "fingerprint": {
            **{f.value: feature_map[f] for f in Feature},
            "vector_length": len(Feature),
        },
    }


def _fetch_and_store(
    repo: SongRepository,
    session: Session,
    track: DeezerTrack,
) -> Song:
    """Fetch audio, extract features, and store the new song + fingerprint.

    Returns the newly persisted `Song`.
    """
    preview_url = track["preview"]
    audio_bytes = fetch_snippet(preview_url)
    mono, sr = load_audio(audio_bytes, filename=preview_url)
    features = collapse_features(extract_features(mono, sr))

    song = repo.create_song_and_fingerprint(
        _to_song_data(track), features, AudioFormat.MP3, sr
    )
    session.commit()
    return song


def process_fingerprint(
    session: Session, track: DeezerTrack, repo: SongRepository
) -> FingerprintResponse:
    """Process a confirmed Deezer track into a stored fingerprint.

    Args:
        session: Active SQLAlchemy session.
        track: Upstream `DeezerTrack` with deezer_id, title, isrc, duration,
            preview, artist, album (artist/album may be objects; flattened
            at entry).
        repo: Repository for song persistence, bound to *session*.

    Returns:
        A `FingerprintResponse` with `song_id`, `deezer_id`, `isrc`, and a
        `fingerprint` dict of the 8 collapsed feature scalars keyed by
        `Feature` snake_case names, plus `vector_length` (== `len(Feature)`).

        Whether the fingerprint was reused from a prior ISRC match or freshly
        generated is observable only via logging (`reused=true/false`), not
        from the return value (see `contracts/search-api.md`).
    """
    isrc = track["isrc"]

    existing = repo.find_by_isrc(isrc)
    if existing is not None:
        log_fingerprint_outcome(
            isrc,
            existing.deezer_id,
            str(existing.id),
            reused=True,
            elapsed=0.0,
            target=logger,
        )
        return _build_response(existing, _feature_map(existing))

    with timer() as elapsed:
        song = _fetch_and_store(repo, session, track)

    log_fingerprint_outcome(
        isrc,
        song.deezer_id,
        str(song.id),
        reused=False,
        elapsed=elapsed(),
        target=logger,
    )

    return _build_response(song, _feature_map(song))
