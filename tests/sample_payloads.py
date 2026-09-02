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

SUCCESS_RESPONSE = {
    "status": "success",
    "song_id": "0195a1b8-0000-7000-8000-000000000000",
    "deezer_id": 3135556,
    "isrc": "GBDUW0000059",
    "fingerprint": {
        "spectral_centroid": 2154.32,
        "rms": 0.045,
        "spectral_bandwidth": 1820.15,
        "spectral_contrast": 18.42,
        "spectral_flatness": 0.012,
        "spectral_rolloff": 4350.80,
        "zero_crossing_rate": 0.085,
        "mfcc": 12.34,
        "vector_length": 8,
    },
}

FINGERPRINT_FIELDS: list[str] = [
    "spectral_centroid",
    "rms",
    "spectral_bandwidth",
    "spectral_contrast",
    "spectral_flatness",
    "spectral_rolloff",
    "zero_crossing_rate",
    "mfcc",
]
