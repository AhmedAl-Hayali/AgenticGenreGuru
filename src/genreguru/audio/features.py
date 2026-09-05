"""The acoustic feature vocabulary extracted per audio snippet.

`Feature` is the single source of truth for the 8 feature names used across
genreguru.audio (extract + collapse), the fingerprint service, the repository
layer, and tests. It is a `StrEnum` so members coerce to their snake_case
names for dictionary keys, iteration, and `getattr` against the fixed
`SongFingerprint` column names (data-model.md).
"""

import enum


class Feature(enum.StrEnum):
    """The 8 acoustic features extracted per audio snippet.

    Declaration order matches the canonical feature ordering used across the
    codebase (data-model.md `song_fingerprints` columns). Because it is a
    `StrEnum`, each member's string value is its snake_case name — the
    database column name, dict key, and log label all derive from it. Each
    member also carries its human-readable display `label` (bound via
    `__new__`), so the frontend label map is built structurally as
    `{f.value: f.label for f in Feature}`.
    """

    label: str  # declared for type checkers; bound per-member in `__new__`

    def __new__(cls, value: str, label: str) -> Feature:
        """Construct a `Feature` member with string value `value` and display `label`."""
        instance = str.__new__(cls, value)
        # assigned value is a (value, label) tuple; keep the string
        instance._value_ = value
        instance.label = label
        return instance

    SPECTRAL_CENTROID = "spectral_centroid", "Spectral Centroid (Hz)"
    """Spectral centroid (Hz): spectral brightness / center of mass."""

    RMS = "rms", "RMS"
    """Root mean square energy: perceived loudness / frame energy."""

    SPECTRAL_BANDWIDTH = "spectral_bandwidth", "Spectral Bandwidth (Hz)"
    """Spectral bandwidth (Hz): spread of the spectrum around its centroid."""

    SPECTRAL_CONTRAST = "spectral_contrast", "Spectral Contrast (dB)"
    """Spectral contrast (dB): difference between spectral peaks and valleys."""

    SPECTRAL_FLATNESS = "spectral_flatness", "Spectral Flatness"
    """Spectral flatness [0,1]: noise-vs-tonality (0 tonal, ~1 noise)."""

    SPECTRAL_ROLLOFF = "spectral_rolloff", "Spectral Rolloff (Hz)"
    """Spectral roll-off (Hz): frequency below ~85% of spectral energy."""

    ZERO_CROSSING_RATE = "zero_crossing_rate", "Zero Crossing Rate"
    """Zero crossing rate: harmonic-vs-percussive content."""

    MFCC = "mfcc", "MFCC"
    """MFCC (20 coefficients): timbre / spectral shape.

    Collapsed to one scalar in V1 (mean); future versions may keep many
    frames as many `n_mfcc` scalars.
    """
