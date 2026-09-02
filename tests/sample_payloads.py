"""Shared Deezer/payload fixtures for the contract tests.

Single canonical definitions for the track used across the search and
confirm contract suites, so a field edit lands in one place and both
endpoints exercise the same realistic payload.
"""

from genreguru.dto import DeezerTrack

DEEZER_MATCH: DeezerTrack = {
    "deezer_id": 3135556,
    "title": "Harder, Better, Faster, Stronger",
    "isrc": "GBDUW0000059",
    "duration": 226,
    "preview": "https://cdnt-preview.dzcdn.net/api/1/1/abc/def/0/abc.mp3?hdnea=exp=123",
    "artist": {"id": 27, "name": "Daft Punk"},
    "album": {"id": 302127, "title": "Discovery"},
}

DEEZER_MATCHES: list[DeezerTrack] = [DEEZER_MATCH]
