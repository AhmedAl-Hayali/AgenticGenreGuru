"""SQLAlchemy models for Song and SongFingerprint.

Schema authority: specs/001-song-fingerprint-engine/data-model.md.

Both tables use native PostgreSQL `uuidv7()` as the column default
(PostgreSQL 18+), with no application-layer fallback. Models are kept
logging-free (SRP): persistence logging lives in the repository layer
(task T024). Mixins from `genreguru.db.base` provide audit columns
and UUID primary keys.
"""

import enum
import uuid

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from genreguru.db.base import Base, TimestampedMixin, UuidMixin


class AudioFormat(enum.Enum):
    """Supported audio formats for music metadata."""

    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    M4A = "m4a"


class Song(Base, TimestampedMixin, UuidMixin):
    """A track retrieved from Deezer search results (data-model.md `songs`).

    Deduplication matches on `isrc`; both `isrc` and `deezer_id` are unique
    so a track can never be stored twice.
    """

    __tablename__ = "songs"
    __table_args__ = (
        UniqueConstraint("deezer_id"),
        UniqueConstraint("isrc"),
    )

    deezer_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    isrc: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    artist: Mapped[str] = mapped_column(String(255), nullable=False)
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_url: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)

    fingerprint: Mapped[SongFingerprint] = relationship(
        back_populates="song", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return a string representation of the Song instance."""
        return f"<Song id={self.id} title={self.title!r} artist={self.artist!r}>"


class SongFingerprint(Base, TimestampedMixin, UuidMixin):
    """Extracted DSP acoustic feature vector linked one-to-one to a Song."""

    __tablename__ = "song_fingerprints"

    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id"),
        unique=True,
        nullable=False,
    )
    spectral_centroid: Mapped[float] = mapped_column(Float, nullable=False)
    rms: Mapped[float] = mapped_column(Float, nullable=False)
    spectral_bandwidth: Mapped[float] = mapped_column(Float, nullable=False)
    spectral_contrast: Mapped[float] = mapped_column(Float, nullable=False)
    spectral_flatness: Mapped[float] = mapped_column(Float, nullable=False)
    spectral_rolloff: Mapped[float] = mapped_column(Float, nullable=False)
    zero_crossing_rate: Mapped[float] = mapped_column(Float, nullable=False)
    mfcc: Mapped[float] = mapped_column(Float, nullable=False)
    audio_format: Mapped[AudioFormat] = mapped_column(ENUM(AudioFormat), nullable=False)
    sample_rate: Mapped[int] = mapped_column(
        Integer, server_default=text("22050"), nullable=False
    )

    song: Mapped[Song] = relationship(back_populates="fingerprint")

    def __repr__(self) -> str:
        """Return a string representation of the SongFingerprint instance."""
        return f"<SongFingerprint id={self.id} song_id={self.song_id}>"
