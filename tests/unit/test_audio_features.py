"""Unit tests for mono downmix loader + 8-feature extraction (T014).

Covers all 8 DSP feature extraction functions plus their arithmetic-mean
collapse to scalars, with a silent/nonmusical input edge case (REQ-016).
`extract_*` returns raw per-frame ndarrays; `collapse_feature` /
`collapse_features` reduce them to scalars. These tests exercise the collapsed
scalar layer (the current production consumption point); raw-array tests are
outlined in phase_3_notes.md.

Tests import from `genreguru.audio.feature_extract` (T021) and use numpy arrays
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
AUDIBLE_LOW_HZ = 100
AUDIBLE_HIGH_HZ = 8000
BANDWIDTH_BIN_FACTOR = 4


def _mag(audio):
    """Shared magnitude |STFT| input for the spectral feature extractors."""
    return feature_extract._magnitude_spectrogram(audio)


MAG_SINE = _mag(SINE)
MAG_SILENT = _mag(SILENT)
MAG_LOW_ENERGY = _mag(LOW_ENERGY)


@pytest.mark.parametrize(
    "feature, extract, args",
    [
        (
            Feature.SPECTRAL_CENTROID,
            feature_extract.extract_spectral_centroid,
            (MAG_SINE, SAMPLE_RATE),
        ),
        (Feature.RMS, feature_extract.extract_rms, (SINE,)),
        (
            Feature.SPECTRAL_BANDWIDTH,
            feature_extract.extract_spectral_bandwidth,
            (MAG_SINE, SAMPLE_RATE),
        ),
        (
            Feature.SPECTRAL_CONTRAST,
            feature_extract.extract_spectral_contrast,
            (MAG_SINE, SAMPLE_RATE),
        ),
        (
            Feature.SPECTRAL_FLATNESS,
            feature_extract.extract_spectral_flatness,
            (MAG_SINE,),
        ),
        (
            Feature.SPECTRAL_ROLLOFF,
            feature_extract.extract_spectral_rolloff,
            (MAG_SINE, SAMPLE_RATE),
        ),
        (
            Feature.ZERO_CROSSING_RATE,
            feature_extract.extract_zero_crossing_rate,
            (SINE,),
        ),
        (
            Feature.MFCC,
            feature_extract.extract_mfcc,
            (MAG_SINE, SAMPLE_RATE),
        ),
    ],
)
def test_collapse_returns_float(feature, extract, args):
    """Collapsed scalar must be a Python float."""
    assert isinstance(feature_collapse.collapse_feature(extract(*args), feature), float)


class TestSpectralCentroid:
    """Verify `extract_spectral_centroid` numeric output and boundary behaviour."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_centroid(cls):
        """Collapsed spectral centroid of the `SINE_FREQUENCY` Hz sine wave."""
        raw = feature_extract.extract_spectral_centroid(MAG_SINE, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_CENTROID)

    @pytest.fixture(scope="class")
    @classmethod
    def silent_centroid(cls):
        """Collapsed spectral centroid of silent audio."""
        raw = feature_extract.extract_spectral_centroid(MAG_SILENT, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_CENTROID)

    @pytest.fixture(scope="class")
    @classmethod
    def low_energy_centroid(cls):
        """Collapsed spectral centroid of the low-energy input."""
        raw = feature_extract.extract_spectral_centroid(MAG_LOW_ENERGY, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_CENTROID)

    def test_sine_centroid_is_positive(self, sine_centroid):
        """A `SINE_FREQUENCY` sine has energy concentrated above 0 Hz."""
        assert sine_centroid > 0

    def test_matches_ground_truth(self, sine_centroid):
        """Centroid of a pure tone must sit close to its frequency."""
        assert sine_centroid == pytest.approx(SINE_FREQUENCY, rel=REL_TOLERANCE)

    def test_sine_centroid_value_within_audible_bounds(self, sine_centroid):
        """Centroid of a pure tone should fall within the audible range."""
        assert AUDIBLE_LOW_HZ < sine_centroid < AUDIBLE_HIGH_HZ

    def test_silent_input(self, silent_centroid):
        """Silent audio must still produce a finite value (no NaN/inf)."""
        assert np.isfinite(silent_centroid)

    def test_low_energy(self, low_energy_centroid):
        """Near-zero amplitude audio must not cause division-by-zero."""
        assert np.isfinite(low_energy_centroid)


class TestRMS:
    """Verify `extract_rms` root-mean-square amplitude calculation."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_rms(cls):
        """Collapsed RMS of the `SINE_FREQUENCY` Hz sine wave."""
        return feature_collapse.collapse_feature(
            feature_extract.extract_rms(SINE), Feature.RMS
        )

    @pytest.fixture(scope="class")
    @classmethod
    def silent_rms(cls):
        """Collapsed RMS of silent audio."""
        return feature_collapse.collapse_feature(
            feature_extract.extract_rms(SILENT), Feature.RMS
        )

    def test_sine_rms_value_within_normalized_bounds(self, sine_rms):
        """RMS of a `SINE_AMPLITUDE`-amplitude sine must be positive, below 1."""
        assert 0 < sine_rms < 1

    def test_matches_ground_truth(self, sine_rms):
        """RMS of a pure tone must sit close to its amplitude divided by sqrt(2).

        Source: https://en.wikipedia.org/wiki/Root_mean_square
        """
        assert sine_rms == pytest.approx(SINE_AMPLITUDE / np.sqrt(2), rel=REL_TOLERANCE)

    def test_silent_rms_zero(self, silent_rms):
        """Silent audio must yield RMS of zero."""
        assert silent_rms == pytest.approx(0, abs=1e-10)


class TestSpectralBandwidth:
    """Verify `extract_spectral_bandwidth` spread measurement."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_bandwidth(cls):
        """Collapsed bandwidth of the `SINE_FREQUENCY` Hz sine, edge STFT frames trimmed.

        `center=True` zero-pads the first/last frames, so their bandwidth is an
        edge artifact (~64-85 bins) unrelated to the tone; trimming 2 frames per
        side leaves the physical pure-tone leak (~1.09 bins). Test-only trim --
        production collapse keeps all frames.
        """
        raw = feature_extract.extract_spectral_bandwidth(MAG_SINE, SAMPLE_RATE)
        return feature_collapse.collapse_feature(
            raw[..., 2:-2], Feature.SPECTRAL_BANDWIDTH
        )

    def test_sine_bandwidth_is_positive(self, sine_bandwidth):
        """Bandwidth must be positive for any non-degenerate input."""
        assert sine_bandwidth > 0

    def test_sine_bandwidth_value_within_narrow_bounds(self, sine_bandwidth):
        """Pure-tone bandwidth is a small multiple of the FFT bin width sr/n_fft."""
        assert (
            0
            < sine_bandwidth
            < BANDWIDTH_BIN_FACTOR * (SAMPLE_RATE / feature_extract._N_FFT)
        )


class TestSpectralContrast:
    """Verify `extract_spectral_contrast` peak-valley difference."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_contrast(cls):
        """Collapsed spectral contrast of the `SINE_FREQUENCY` Hz sine wave."""
        raw = feature_extract.extract_spectral_contrast(MAG_SINE, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_CONTRAST)

    @pytest.fixture(scope="class")
    @classmethod
    def silent_contrast(cls):
        """Collapsed spectral contrast of silent audio."""
        raw = feature_extract.extract_spectral_contrast(MAG_SILENT, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_CONTRAST)

    @pytest.fixture(scope="class")
    @classmethod
    def low_energy_contrast(cls):
        """Collapsed spectral contrast of the low-energy input."""
        raw = feature_extract.extract_spectral_contrast(MAG_LOW_ENERGY, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_CONTRAST)

    def test_sine_contrast_is_positive(self, sine_contrast):
        """A pure tone has clear peaks, so contrast must be non-negative."""
        assert sine_contrast >= 0

    def test_sine_contrast_is_nonzero(self, sine_contrast):
        """A pure tone yields a strong peak-valley difference."""
        assert sine_contrast > 0

    def test_silent_contrast_is_finite(self, silent_contrast):
        """Silent audio must not produce NaN/inf contrast."""
        assert np.isfinite(silent_contrast)

    def test_low_energy_contrast_is_finite(self, low_energy_contrast):
        """Near-zero amplitude must not produce NaN/inf contrast."""
        assert np.isfinite(low_energy_contrast)


class TestSpectralFlatness:
    """Verify `extract_spectral_flatness` tonality ratio [0, 1]."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_flatness(cls):
        """Collapsed spectral flatness of the `SINE_FREQUENCY` Hz sine wave."""
        raw = feature_extract.extract_spectral_flatness(MAG_SINE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_FLATNESS)

    @pytest.fixture(scope="class")
    @classmethod
    def silent_flatness(cls):
        """Collapsed spectral flatness of silent audio."""
        raw = feature_extract.extract_spectral_flatness(MAG_SILENT)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_FLATNESS)

    def test_sine_flatness_value_within_unit_bounds(self, sine_flatness):
        """Flatness must lie within [0, 1] by definition."""
        assert 0 <= sine_flatness <= 1

    def test_sine_flatness_is_low(self, sine_flatness):
        """A pure tone is tonal, so its flatness must sit near the 0 (peaked) end."""
        assert sine_flatness < 0.5

    def test_silent_flatness_is_finite(self, silent_flatness):
        """Silent audio must not produce NaN/inf flatness."""
        assert np.isfinite(silent_flatness)


class TestSpectralRolloff:
    """Verify `extract_spectral_rolloff` frequency threshold."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_rolloff(cls):
        """Collapsed spectral rolloff of the `SINE_FREQUENCY` Hz sine wave."""
        raw = feature_extract.extract_spectral_rolloff(MAG_SINE, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.SPECTRAL_ROLLOFF)

    def test_sine_rolloff_is_positive(self, sine_rolloff):
        """Rolloff frequency must be positive for non-silent audio."""
        assert sine_rolloff > 0

    def test_sine_rolloff_value_within_audible_bounds(self, sine_rolloff):
        """`SINE_FREQUENCY` sine rolloff should fall within the audible range."""
        assert AUDIBLE_LOW_HZ < sine_rolloff < AUDIBLE_HIGH_HZ

    def test_matches_ground_truth(self, sine_rolloff):
        """Rolloff of a pure tone must sit near the tone's frequency."""
        assert sine_rolloff == pytest.approx(SINE_FREQUENCY, rel=REL_TOLERANCE)


class TestZeroCrossingRate:
    """Verify `extract_zero_crossing_rate` sign-change frequency."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_zero_crossing_rate(cls):
        """Collapsed zero crossing rate of the `SINE_FREQUENCY` Hz sine wave."""
        raw = feature_extract.extract_zero_crossing_rate(SINE)
        return feature_collapse.collapse_feature(raw, Feature.ZERO_CROSSING_RATE)

    @pytest.fixture(scope="class")
    @classmethod
    def silent_zero_crossing_rate(cls):
        """Collapsed zero crossing rate of silent audio."""
        raw = feature_extract.extract_zero_crossing_rate(SILENT)
        return feature_collapse.collapse_feature(raw, Feature.ZERO_CROSSING_RATE)

    def test_sine_zero_crossing_rate_is_positive(self, sine_zero_crossing_rate):
        """A `SINE_FREQUENCY` Hz sine crosses zero frequently; rate must be positive."""
        assert sine_zero_crossing_rate > 0

    def test_silent_zero(self, silent_zero_crossing_rate):
        """Silent audio has no sign changes."""
        assert silent_zero_crossing_rate == pytest.approx(0, abs=1e-10)


class TestMFCC:
    """Verify `extract_mfcc` mel-frequency cepstral coefficient."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_mfcc(cls):
        """Collapsed mean MFCC of the `SINE_FREQUENCY` Hz sine wave."""
        raw = feature_extract.extract_mfcc(MAG_SINE, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.MFCC)

    @pytest.fixture(scope="class")
    @classmethod
    def silent_mfcc(cls):
        """Collapsed mean MFCC of silent audio."""
        raw = feature_extract.extract_mfcc(MAG_SILENT, SAMPLE_RATE)
        return feature_collapse.collapse_feature(raw, Feature.MFCC)

    def test_sine_finite(self, sine_mfcc):
        """MFCC of a sine must be finite."""
        assert np.isfinite(sine_mfcc)

    def test_silent_finite(self, silent_mfcc):
        """MFCC of silent audio must be finite (no NaN from log)."""
        assert np.isfinite(silent_mfcc)

    def test_raw_coefficient_shape(self):
        """`extract_mfcc` must return the `(n_mfcc, n_frames)` shape."""
        raw = feature_extract.extract_mfcc(MAG_SINE, SAMPLE_RATE)
        assert raw.ndim == 2
        assert raw.shape[0] == 20
        assert raw.shape[1] > 0

    def test_raw_all_coefficients_finite(self):
        """Every MFCC coefficient and frame must be finite."""
        raw = feature_extract.extract_mfcc(MAG_SINE, SAMPLE_RATE)
        assert np.all(np.isfinite(raw))


class TestExtractFeatures:
    """Verify `extract_features` + `collapse_features` yield an 8-key scalar dict."""

    @pytest.fixture(scope="class")
    @classmethod
    def sine_features(cls):
        """Full 8-key collapsed feature dict for the `SINE_FREQUENCY` Hz sine wave."""
        return feature_collapse.collapse_features(
            feature_extract.extract_features(SINE, SAMPLE_RATE)
        )

    @pytest.fixture(scope="class")
    @classmethod
    def silent_features(cls):
        """Full 8-key collapsed feature dict for silent audio."""
        return feature_collapse.collapse_features(
            feature_extract.extract_features(SILENT, SAMPLE_RATE)
        )

    @pytest.fixture(scope="class")
    @classmethod
    def low_energy_features(cls):
        """Full 8-key collapsed feature dict for the low-energy input."""
        return feature_collapse.collapse_features(
            feature_extract.extract_features(LOW_ENERGY, SAMPLE_RATE)
        )

    def test_returns_dict_with_expected_feature_keys(self, sine_features):
        """Result must be a dict with exactly the expected feature keys."""
        assert isinstance(sine_features, dict)
        assert set(sine_features.keys()) == set(Feature)

    def test_all_values_are_finite_floats(self, sine_features):
        """Every feature value must be a finite float."""
        for key in Feature:
            assert isinstance(sine_features[key], float)
            assert np.isfinite(sine_features[key])

    def test_all_positive_for_sine(self, sine_features):
        """All features except MFCC must be positive for a pure tone."""
        for key in Feature:
            if key is Feature.MFCC:
                continue
            assert sine_features[key] > 0

    def test_silent_input_produces_valid_vector(self, silent_features):
        """Silent audio must still yield a full finite feature vector."""
        assert len(silent_features) == len(Feature)
        for key in Feature:
            assert np.isfinite(silent_features[key])

    def test_low_energy_input(self, low_energy_features):
        """Near-zero amplitude must not produce NaN or inf in any feature."""
        assert len(low_energy_features) == len(Feature)
        for key in Feature:
            assert np.isfinite(low_energy_features[key])
