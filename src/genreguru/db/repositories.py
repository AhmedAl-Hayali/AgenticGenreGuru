"""Repository layer for Song and SongFingerprint persistence.

Implements deduplication-by-ISRC per data-model.md.
"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from genreguru.audio.features import Feature
from genreguru.db.models import AudioFormat, Song, SongFingerprint
from genreguru.dto import FeatureScalars, SongData

logger = logging.getLogger(__name__)


class SongRepository:
    """Thin wrapper around a SQLAlchemy session for Song/Fingerprint CRUD."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_isrc(self, isrc: str) -> Song | None:
        """Return the Song matching *isrc*, or ``None``.

        Logs the lookup outcome at INFO level (hit/miss).
        """
        song = Song.find_by_isrc(self._session, isrc)
        if song is not None:
            logger.info("isrc lookup hit isrc=%s song_id=%s", isrc, song.id)
        else:
            logger.info("isrc lookup miss isrc=%s", isrc)
        return song

    def create_song_and_fingerprint(
        self,
        song_data: SongData,
        features: FeatureScalars,
        audio_format: AudioFormat = AudioFormat.MP3,
        sample_rate: int = 22050,
    ) -> Song:
        """Create a Song + SongFingerprint, or return existing Song on ISRC match.

        Deduplication: if a Song with the same ISRC already exists, return
        it without creating a duplicate fingerprint. Concurrent duplicate
        inserts (TOCTOU race) are handled gracefully — the unique-violation
        is logged at WARNING and the existing song is returned.

        Args:
            song_data: `SongData` with deezer_id, isrc, title, artist, album,
                preview_url, duration (album key always present, value may be
                None).
            features: The 8 collapsed feature scalars keyed by `Feature`.
            audio_format: Encoding format of the snippet (default MP3).
            sample_rate: Sampling rate in Hz (default 22050).

        Returns:
            The Song (newly created or existing).
        """
        isrc = song_data["isrc"]
        existing = Song.find_by_isrc(self._session, isrc)

        if existing is not None:
            return existing

        logger.info(
            "creating song isrc=%s deezer_id=%s",
            isrc,
            song_data["deezer_id"],
        )

        song = Song(
            deezer_id=song_data["deezer_id"],
            isrc=isrc,
            title=song_data["title"],
            artist=song_data["artist"],
            album=song_data["album"],
            preview_url=song_data["preview_url"],
            duration=song_data["duration"],
        )
        try:
            with self._session.begin_nested():
                self._session.add(song)
                self._session.flush()
        except IntegrityError:
            logger.warning(
                "concurrent duplicate isrc=%s deezer_id=%s",
                isrc,
                song_data["deezer_id"],
            )
            existing = Song.find_by_isrc(self._session, isrc)
            if existing is None:
                logger.warning(
                    "unexpected unique-violation (non-ISRC collision) isrc=%s deezer_id=%s",
                    isrc,
                    song_data["deezer_id"],
                )
                raise
            return existing

        fingerprint = SongFingerprint(
            song_id=song.id,
            **{f.value: features[f] for f in Feature},
            audio_format=audio_format,
            sample_rate=sample_rate,
        )
        self._session.add(fingerprint)
        self._session.flush()

        logger.info(
            "song created song_id=%s isrc=%s deezer_id=%s",
            song.id,
            isrc,
            song_data["deezer_id"],
        )
        return song
