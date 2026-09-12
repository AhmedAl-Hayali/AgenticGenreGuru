"""Unit tests for the SQLAlchemy model `__repr__` methods (`genreguru/db/models.py`).

Models keep persistence concerns out of the reprs; `__repr__` executes on any
transient instance, so the factories' `.build()` strategy (no DB, no session)
is sufficient to exercise every repr body.
"""

from genreguru.db.models import Song, SongArtist, SongFingerprint
from tests.factories import SongArtistFactory, SongFactory, SongFingerprintFactory


class TestModelRepr:
    """Pin each model's `__repr__` output against a built (unpersisted) instance."""

    def test_song_repr(self):
        """A built Song must round-trip id/title/artist into the repr."""
        song: Song = SongFactory.build()
        assert repr(song) == (
            f"<Song id={song.id} title={song.title!r} artist={song.artist!r}>"
        )

    def test_song_artist_repr(self):
        """A built SongArtist must round-trip deezer_id/position/name."""
        artist: SongArtist = SongArtistFactory.build()
        assert repr(artist) == (
            f"<SongArtist deezer_id={artist.deezer_id} "
            f"position={artist.position} name={artist.name!r}>"
        )

    def test_song_fingerprint_repr(self):
        """A built SongFingerprint must round-trip id and song_id."""
        fp: SongFingerprint = SongFingerprintFactory.build()
        assert repr(fp) == f"<SongFingerprint id={fp.id} song_id={fp.song_id}>"
