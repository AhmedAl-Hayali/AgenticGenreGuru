"""GenreGuru — acoustic fingerprinting core library.

**GenreGuru** takes a song title, pulls a 30-second Deezer preview,
runs a DSP pipeline extracting 8 acoustic features, and stores the
fingerprint vector in PostgreSQL. Query stored fingerprints by cosine
similarity to find sonically similar tracks.

This package provides the standalone core library. It is **silent by
default** — a `NullHandler` is attached at import time. Logging is
activated by the application (Django or CLI) via `LoggingManager.setup()`.

Design authority: `docs/001-song-fingerprint-engine/logging-report.md`.
"""

__docformat__ = "google"

import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
