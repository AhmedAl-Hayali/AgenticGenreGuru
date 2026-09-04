"""Scalar collapse of raw per-frame audio features.

Collapse reduces a raw `extract_*` ndarray from `genreguru.audio.feature_extract`
to a single scalar via the arithmetic mean (V1 downsampling strategy per
data-model.md). Features are addressed by the shared `Feature` enum
(`genreguru.audio.features`); `collapse_features` preserves the enum keys of
`extract_features`, and `collapse_feature(arr, name)` collapses a single
feature.

Keeping collapse in its own module decouples the cheap aggregation policy
from the expensive DSP extraction, so the mean can later be swapped
(median, trimmed mean, weighted mean, ...) without touching extraction.

Module logger: DEBUG per-feature collapse mean.
"""

import logging

import numpy as np

from genreguru.audio.features import Feature

logger = logging.getLogger(__name__)

_FEATURE_LOG_FORMATS = {
    Feature.SPECTRAL_CENTROID: "%.4f",
    Feature.RMS: "%.6f",
    Feature.SPECTRAL_BANDWIDTH: "%.4f",
    Feature.SPECTRAL_CONTRAST: "%.4f",
    Feature.SPECTRAL_FLATNESS: "%.6f",
    Feature.SPECTRAL_ROLLOFF: "%.4f",
    Feature.ZERO_CROSSING_RATE: "%.6f",
    Feature.MFCC: "%.4f",
}


def collapse_feature(feature: np.ndarray, name: Feature) -> float:
    """Collapse a raw `extract_*` ndarray to a scalar via arithmetic mean."""
    val = float(np.mean(feature))
    logger.debug("%s collapse mean=%s", name.value, _FEATURE_LOG_FORMATS[name] % val)
    return val


def collapse_features(
    features_dict: dict[Feature, np.ndarray],
) -> dict[Feature, float]:
    """Collapse each raw feature ndarray to a scalar, preserving `Feature` keys."""
    return {name: collapse_feature(arr, name) for name, arr in features_dict.items()}
