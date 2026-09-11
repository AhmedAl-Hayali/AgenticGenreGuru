"""Shared Deezer/payload fixtures for the contract tests.

Single canonical definitions for the track used across the search and
confirm contract suites, so a field edit lands in one place and both
endpoints exercise the same realistic payload.
"""

from genreguru.dto import Album, Artist, ConfirmTrack, Track


def make_sample_artist(artist_id: int = 27, name: str = "Daft Punk") -> Artist:
    """Helper to build a strongly typed Artist dict fixture."""
    return Artist(id=artist_id, name=name)


# Cover built from the 32-hex `md5_image` via the client's bare-suffix form
# (`contracts/deezer-api.md`): https://cdn-images.dzcdn.net/images/cover/{md5}/300x300.jpg
DEEZER_COVER_URL = (
    "https://cdn-images.dzcdn.net/images/cover/"
    "950fd2a2d0f5f80e3b5f1e9f0b2a3c4d/300x300.jpg"
)

DEEZER_MATCH: Track = {
    "deezer_id": 3135556,
    "title": "Harder, Better, Faster, Stronger",
    "isrc": "GBDUW0000059",
    "duration": 226,
    "preview": "https://cdnt-preview.dzcdn.net/api/1/1/abc/def/0/abc.mp3?hdnea=exp=123",
    "cover": DEEZER_COVER_URL,
    "artists": [make_sample_artist(27, "Daft Punk")],
    "album": Album(id=302127, title="Discovery"),
}

DEEZER_MATCHES: list[Track] = [DEEZER_MATCH]

# Confirm request body: the search match minus the display-only `cover` —
# exactly the backend's 7 required fields (`ConfirmTrack`, contracts/
# search-api.md §2). The frontend strips `cover` on POST, and the confirm
# endpoint rejects extras.
DEEZER_CONFIRM_BODY: ConfirmTrack = {
    "deezer_id": DEEZER_MATCH["deezer_id"],
    "title": DEEZER_MATCH["title"],
    "isrc": DEEZER_MATCH["isrc"],
    "duration": DEEZER_MATCH["duration"],
    "preview": DEEZER_MATCH["preview"],
    "artists": DEEZER_MATCH["artists"],
    "album": DEEZER_MATCH["album"],
}

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
