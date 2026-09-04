"""Eight-feature DSP extraction, returning raw per-frame ndarrays.

Each `extract_*` function computes one feature's temporal frame vector
from a magnitude spectrogram (`mag`) or the raw audio. Collapse to
scalars happens separately in `genreguru.audio.feature_collapse`.

Module logger: WARNING/INFO on zero/low-energy frames, INFO extraction
complete + elapsed (SC-002).
"""

import logging

import numpy as np
from librosa import power_to_db, stft
from librosa.feature import (
    melspectrogram,
    mfcc,
    rms,
    spectral_bandwidth,
    spectral_centroid,
    spectral_contrast,
    spectral_flatness,
    spectral_rolloff,
    zero_crossing_rate,
)

from genreguru.audio.features import Feature
from genreguru.gglogging import timer

logger = logging.getLogger(__name__)

_N_FFT = 2048
_HOP_LENGTH = 512


def _magnitude_spectrogram(audio: np.ndarray) -> np.ndarray:
    """One shared |STFT| so spectral features avoid recomputing the FFT.

    Mirrors librosa's internal S for spectral_* (power=1) so results are
    bit-identical to computing each feature from `y` directly.
    """
    return np.abs(
        stft(
            audio,
            n_fft=_N_FFT,
            hop_length=_HOP_LENGTH,
            center=True,
            pad_mode="constant",
        )
    )


def extract_spectral_centroid(mag: np.ndarray, sr: int) -> np.ndarray:
    """Spectral centroid per frame (Hz).

    Captures spectral "brightness" — the frequency-weighted center of
    mass of each frame's magnitude spectrum.

    Args:
        mag: Shared magnitude spectrogram (from `_magnitude_spectrogram`).
        sr: Sample rate in Hz.

    Returns:
        `(1, n_frames)` ndarray of centroid frequencies in Hz.
    """
    return spectral_centroid(S=mag, sr=sr)


def extract_rms(audio: np.ndarray) -> np.ndarray:
    """Root-mean-square energy per frame.

    Captures frame loudness / energy.

    Args:
        audio: Mono audio signal.

    Returns:
        `(1, n_frames)` ndarray of RMS energy values.
    """
    return rms(y=audio)


def extract_spectral_bandwidth(
    mag: np.ndarray, sr: int, centroid: np.ndarray | None = None
) -> np.ndarray:
    """Spectral bandwidth per frame (Hz).

    Captures how spread the spectrum is around its centroid (brightness
    breadth).

    Args:
        mag: Shared magnitude spectrogram (from `_magnitude_spectrogram`).
        sr: Sample rate in Hz.
        centroid: Precomputed spectral centroid vector, if available.
            Passing it avoids librosa recomputing it internally (shared
            with `extract_spectral_centroid`).

    Returns:
        `(1, n_frames)` ndarray of bandwidths in Hz.
    """
    return spectral_bandwidth(S=mag, sr=sr, centroid=centroid)


def extract_spectral_contrast(mag: np.ndarray, sr: int) -> np.ndarray:
    """Spectral contrast per frame (dB).

    Captures the difference between spectral peaks and valleys across
    octave bands (tonality content).

    Args:
        mag: Shared magnitude spectrogram (from `_magnitude_spectrogram`).
        sr: Sample rate in Hz.

    Returns:
        `(n_bands, n_frames)` ndarray of contrast values in dB.
    """
    return spectral_contrast(S=mag, sr=sr)


def extract_spectral_flatness(mag: np.ndarray) -> np.ndarray:
    """Spectral flatness per frame.

    Captures the noise-vs-tonality axis (range [0,1]): ~0 tonal/peaked,
    ~1 noise/flat.

    Args:
        mag: Shared magnitude spectrogram (from `_magnitude_spectrogram`).

    Returns:
        `(1, n_frames)` ndarray of flatness values.
    """
    return spectral_flatness(S=mag)


def extract_spectral_rolloff(mag: np.ndarray, sr: int) -> np.ndarray:
    """Spectral roll-off frequency per frame (Hz).

    The frequency below which a fixed fraction (default `roll_percent=0.85`)
    of the frame's spectral energy is concentrated.

    Args:
        mag: Shared magnitude spectrogram (from `_magnitude_spectrogram`).
        sr: Sample rate in Hz.

    Returns:
        `(1, n_frames)` ndarray of rolloff frequencies in Hz.
    """
    return spectral_rolloff(S=mag, sr=sr)


def extract_zero_crossing_rate(audio: np.ndarray) -> np.ndarray:
    """Zero crossing rate per frame.

    Captures how often the signal changes sign — a proxy for
    harmonic/percussive content.

    Args:
        audio: Mono audio signal.

    Returns:
        `(1, n_frames)` ndarray of zero-crossing rates.
    """
    return zero_crossing_rate(audio)


def extract_mfcc(mag: np.ndarray, sr: int) -> np.ndarray:
    """MFCC coefficients per frame.

    Captures timbre / spectral shape via 20 mel-frequency cepstral
    coefficients.

    Args:
        mag: Shared magnitude spectrogram (from `_magnitude_spectrogram`).
        sr: Sample rate in Hz.

    Returns:
        `(n_mfcc, n_frames)` ndarray of MFCC coefficients (n_mfcc=20).
        Collapse reduces this to one scalar for V1; future versions may
        keep many `n_mfcc` scalars.
    """
    melspec = melspectrogram(S=mag**2, sr=sr)
    return mfcc(S=power_to_db(melspec), sr=sr, n_mfcc=20)


def extract_features(audio: np.ndarray, sr: int) -> dict[Feature, np.ndarray]:
    """Extract all 8 features, returning a dict of raw per-frame ndarrays keyed by `Feature`.

    Collapse to scalars with `genreguru.audio.feature_collapse.collapse_features`
    (or `collapse_feature(..., name)`), which preserves the `Feature` keys, when a
    single scalar per feature is desired.

    Performance: the STFT is computed ONCE and shared by all 6 spectral
    features (`spectral_centroid`/`spectral_bandwidth`/`spectral_contrast`/
    `spectral_flatness`/`spectral_rolloff`/`mfcc`) instead of each doing its
    own redundant FFT. The spectral centroid vector is computed ONCE and
    reused by `spectral_bandwidth` (which would otherwise recompute it
    internally). `rms` and `zero_crossing_rate` stay in the time domain.
    """
    with timer() as elapsed:
        total_energy = float(np.sum(audio**2))
        if total_energy < 1e-12:
            logger.warning(
                "zero/low-energy input detected (total_energy=%.2e)", total_energy
            )

        mag = _magnitude_spectrogram(audio)

        centroid = extract_spectral_centroid(mag, sr)

        result = {
            Feature.SPECTRAL_CENTROID: centroid,
            Feature.RMS: extract_rms(audio),
            Feature.SPECTRAL_BANDWIDTH: extract_spectral_bandwidth(
                mag, sr, centroid=centroid
            ),
            Feature.SPECTRAL_CONTRAST: extract_spectral_contrast(mag, sr),
            Feature.SPECTRAL_FLATNESS: extract_spectral_flatness(mag),
            Feature.SPECTRAL_ROLLOFF: extract_spectral_rolloff(mag, sr),
            Feature.ZERO_CROSSING_RATE: extract_zero_crossing_rate(audio),
            Feature.MFCC: extract_mfcc(mag, sr),
        }

    logger.info("extraction complete: 8 features in %.3fs", elapsed())
    return result
