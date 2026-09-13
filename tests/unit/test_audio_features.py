"""Unit tests for mono downmix loader + 8-feature extraction.

Covers all 8 DSP feature extraction functions plus their arithmetic-mean
collapse to scalars, with a silent/nonmusical input edge case (REQ-016).
`extract_*` returns raw per-frame ndarrays; `collapse_feature` /
`collapse_features` reduce them to scalars. These tests exercise the collapsed
scalar layer (the current production consumption point); raw-array tests are
outlined in phase_3_notes.md.

Tests import from `genreguru.audio.feature_extract` and use numpy arrays
as synthetic audio — no real audio files required (unit scope).
"""

import numpy as np
import pytest

from genreguru.audio import feature_collapse, feature_extract
from genreguru.audio.features import Feature

SAMPLE_RATE = 22050
SINE_TIME_AXIS = np.linspace(0, 1, SAMPLE_RATE, endpoint=False)
SINE_AMPLITUDE = 0.5
SINE_FREQUENCY = 440
SINE = (SINE_AMPLITUDE * np.sin(2 * np.pi * SINE_FREQUENCY * SINE_TIME_AXIS)).astype(
    np.float32
)
SILENT = np.zeros(SAMPLE_RATE, dtype=np.float32)
LOW_ENERGY = (1e-6 * np.random.default_rng(42).random(SAMPLE_RATE)).astype(np.float32)

REL_TOLERANCE = 0.05
BANDWIDTH_BIN_FACTOR = 4


def _mag(audio):
    """Shared magnitude |STFT| input for the spectral feature extractors."""
    return feature_extract._magnitude_spectrogram(audio)


MAG_SINE = _mag(SINE)
MAG_SILENT = _mag(SILENT)
MAG_LOW_ENERGY = _mag(LOW_ENERGY)


def _collapsed(extract, feat, *args, trim=0):
    """Extract then collapse to a scalar; `trim` drops STFT edge frames."""
    raw = extract(*args)
    if trim:
        raw = raw[..., trim:-trim]
    return feature_collapse.collapse_feature(raw, feat)


def _extractor_rows(which):
    """`(feature, extract, args)` rows for the `which` input set."""
    mag, audio = {
        "sine": (MAG_SINE, SINE),
        "silent": (MAG_SILENT, SILENT),
        "low_energy": (MAG_LOW_ENERGY, LOW_ENERGY),
    }[which]
    return [
        (
            Feature.SPECTRAL_CENTROID,
            feature_extract.extract_spectral_centroid,
            (mag, SAMPLE_RATE),
        ),
        (Feature.RMS, feature_extract.extract_rms, (audio,)),
        (
            Feature.SPECTRAL_BANDWIDTH,
            feature_extract.extract_spectral_bandwidth,
            (mag, SAMPLE_RATE),
        ),
        (
            Feature.SPECTRAL_CONTRAST,
            feature_extract.extract_spectral_contrast,
            (mag, SAMPLE_RATE),
        ),
        (Feature.SPECTRAL_FLATNESS, feature_extract.extract_spectral_flatness, (mag,)),
        (
            Feature.SPECTRAL_ROLLOFF,
            feature_extract.extract_spectral_rolloff,
            (mag, SAMPLE_RATE),
        ),
        (
            Feature.ZERO_CROSSING_RATE,
            feature_extract.extract_zero_crossing_rate,
            (audio,),
        ),
        (Feature.MFCC, feature_extract.extract_mfcc, (mag, SAMPLE_RATE)),
    ]


@pytest.mark.parametrize(("feature", "extract", "args"), _extractor_rows("sine"))
def test_collapse_returns_float(feature, extract, args):
    """Collapsed scalar must be a Python float."""
    assert isinstance(feature_collapse.collapse_feature(extract(*args), feature), float)


@pytest.mark.parametrize(
    ("feature", "extract", "args"),
    [
        pytest.param(feature, extract, args, id=f"{feature.name.lower()}:{which}")
        for which in ("silent", "low_energy")
        for feature, extract, args in _extractor_rows(which)
    ],
)
def test_edge_inputs_stay_finite(feature, extract, args):
    """Silent/low-energy inputs must collapse to a finite scalar for every feature."""
    assert np.isfinite(feature_collapse.collapse_feature(extract(*args), feature))


class TestSpectralCentroid:
    """Verify `extract_spectral_centroid` numeric output and boundary behaviour."""

    def test_matches_ground_truth(self):
        """Centroid of a pure tone must sit close to its frequency."""
        value = _collapsed(
            feature_extract.extract_spectral_centroid,
            Feature.SPECTRAL_CENTROID,
            MAG_SINE,
            SAMPLE_RATE,
        )
        assert value == pytest.approx(SINE_FREQUENCY, rel=REL_TOLERANCE)


class TestRMS:
    """Verify `extract_rms` root-mean-square amplitude calculation."""

    def test_matches_ground_truth(self):
        """RMS of a pure tone must sit close to its amplitude divided by sqrt(2).

        Source: https://en.wikipedia.org/wiki/Root_mean_square
        """
        value = _collapsed(feature_extract.extract_rms, Feature.RMS, SINE)
        assert value == pytest.approx(SINE_AMPLITUDE / np.sqrt(2), rel=REL_TOLERANCE)

    def test_silent_rms_zero(self):
        """Silent audio must yield RMS of zero."""
        value = _collapsed(feature_extract.extract_rms, Feature.RMS, SILENT)
        assert value == pytest.approx(0, abs=1e-10)


class TestSpectralBandwidth:
    """Verify `extract_spectral_bandwidth` spread measurement."""

    def test_sine_bandwidth_value_within_narrow_bounds(self):
        """Pure-tone bandwidth is a small multiple of the FFT bin width sr/n_fft.

        `center=True` zero-pads the first/last frames, so their bandwidth is an
        edge artifact; the trim drops those frames. Test-only trim --
        production collapse keeps all frames.
        """
        value = _collapsed(
            feature_extract.extract_spectral_bandwidth,
            Feature.SPECTRAL_BANDWIDTH,
            MAG_SINE,
            SAMPLE_RATE,
            trim=2,
        )
        assert 0 < value < BANDWIDTH_BIN_FACTOR * (SAMPLE_RATE / feature_extract._N_FFT)


class TestSpectralContrast:
    """Verify `extract_spectral_contrast` peak-valley difference."""

    def test_sine_contrast_is_nonzero(self):
        """A pure tone yields a strong peak-valley difference."""
        value = _collapsed(
            feature_extract.extract_spectral_contrast,
            Feature.SPECTRAL_CONTRAST,
            MAG_SINE,
            SAMPLE_RATE,
        )
        assert value > 0


class TestSpectralFlatness:
    """Verify `extract_spectral_flatness` tonality ratio [0, 1]."""

    def test_sine_flatness_value_within_unit_bounds(self):
        """Flatness must lie within [0, 1] by definition."""
        value = _collapsed(
            feature_extract.extract_spectral_flatness,
            Feature.SPECTRAL_FLATNESS,
            MAG_SINE,
        )
        assert 0 <= value <= 1

    def test_sine_flatness_is_low(self):
        """A pure tone is tonal, so its flatness must sit near the 0 (peaked) end."""
        value = _collapsed(
            feature_extract.extract_spectral_flatness,
            Feature.SPECTRAL_FLATNESS,
            MAG_SINE,
        )
        assert value < 0.5


class TestSpectralRolloff:
    """Verify `extract_spectral_rolloff` frequency threshold."""

    def test_matches_ground_truth(self):
        """Rolloff of a pure tone must sit near the tone's frequency."""
        value = _collapsed(
            feature_extract.extract_spectral_rolloff,
            Feature.SPECTRAL_ROLLOFF,
            MAG_SINE,
            SAMPLE_RATE,
        )
        assert value == pytest.approx(SINE_FREQUENCY, rel=REL_TOLERANCE)


class TestZeroCrossingRate:
    """Verify `extract_zero_crossing_rate` sign-change frequency."""

    def test_sine_zero_crossing_rate_is_positive(self):
        """A `SINE_FREQUENCY` Hz sine crosses zero frequently; rate must be positive."""
        value = _collapsed(
            feature_extract.extract_zero_crossing_rate,
            Feature.ZERO_CROSSING_RATE,
            SINE,
        )
        assert value > 0

    def test_silent_zero(self):
        """Silent audio has no sign changes."""
        value = _collapsed(
            feature_extract.extract_zero_crossing_rate,
            Feature.ZERO_CROSSING_RATE,
            SILENT,
        )
        assert value == pytest.approx(0, abs=1e-10)


class TestMFCC:
    """Verify `extract_mfcc` mel-frequency cepstral coefficient."""

    def test_raw_coefficient_array(self):
        """`extract_mfcc` must return the `(n_mfcc, n_frames)` shape, all finite."""
        raw = feature_extract.extract_mfcc(MAG_SINE, SAMPLE_RATE)
        assert raw.ndim == 2
        assert raw.shape[0] == 20
        assert raw.shape[1] > 0
        assert np.all(np.isfinite(raw))


class TestExtractFeatures:
    """Verify `extract_features` + `collapse_features` yield an 8-key scalar dict."""

    def test_returns_dict_with_expected_feature_keys(self):
        """Result must be a dict of finite floats keyed by every feature."""
        features = feature_collapse.collapse_features(
            feature_extract.extract_features(SINE, SAMPLE_RATE)
        )
        assert isinstance(features, dict)
        assert set(features.keys()) == set(Feature)
        for key in Feature:
            assert isinstance(features[key], float)
            assert np.isfinite(features[key])

    def test_all_positive_for_sine(self):
        """All features except MFCC must be positive for a pure tone."""
        features = feature_collapse.collapse_features(
            feature_extract.extract_features(SINE, SAMPLE_RATE)
        )
        for key in Feature:
            if key is Feature.MFCC:
                continue
            assert features[key] > 0

    def test_silent_input_produces_valid_vector(self):
        """Silent audio must still yield a full finite feature vector."""
        features = feature_collapse.collapse_features(
            feature_extract.extract_features(SILENT, SAMPLE_RATE)
        )
        for key in Feature:
            assert np.isfinite(features[key])
