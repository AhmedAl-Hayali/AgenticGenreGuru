"""Unit tests for `genreguru.audio.loader` format detection + decode guard.

Covers `_detect_format` magic-byte/filename mapping (wav/flac/ogg/mp3 inputs
are real files generated via `soundfile`; m4a is handcrafted because the test
environment lacks an MPEG-4 encoder), and the `load_audio` pre-decode guard.
The decode path is exercised for real on a generated wav and mp3.
"""

import io

import numpy as np
import pytest
import soundfile as sf

from genreguru.audio import loader
from genreguru.audio._format_magic import M4A_LEADING_SIZES
from genreguru.errors import AudioProcessingError

_SAMPLE_RATE = 22050
_FRAMES = 2048

# Magic headers with no recognized format, used to exercise the fallback and
# invalid-input paths.
_UNKNOWN_MAGIC = b"\xde\xad"

# MPEG-1/2/2.5 frame-sync samples: `0xFF` followed by a byte whose top 3 bits
# are set (the MPEG_SYNC_BYTE/MPEG_SYNC_MASK rule). Other low-byte values with
# 0xE0 set are equally valid and need not be enumerated; these choices are
# arbitrary representatives.
_MPEG_SYNC_HEADERS = (b"\xff\xfb", b"\xff\xf3", b"\xff\xe3", b"\xff\xf2")

# MP4 box magic built from the sourced `M4A_LEADING_SIZES` (recognized) plus a
# hand-written unrecognized leading size, each followed by the `ftyp` box type.
_RECOGNIZED_FTYP_ATOMS = tuple(size + b"ftyp" for size in M4A_LEADING_SIZES)
_UNRECOGNIZED_FTYP_ATOM = b"\x00\x00\x00\x24ftyp"  # leading size 0x24


def _snippet(
    fmt: str,
    subtype: str | None = None,
    data: np.ndarray | None = None,
) -> bytes:
    """Encode a tiny silent clip to *fmt* bytes (real file header + payload).

    `_detect_format` keys only on leading magic bytes, never on codec/subtype,
    so each format is exercised once with its default subtype. Ogg passes an
    explicit `vorbis` subtype only because libsndfile requires one for Ogg
    output; other formats use their defaults. Multi-subtype cases would re-test
    a property the detector cannot distinguish.

    `data` defaults to a mono (1D) clip; pass a 2D `(frames, channels)` array
    (e.g. via `np.stack`) to emit multichannel audio.
    """
    if data is None:
        data = np.zeros(_FRAMES, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(
        buf,
        data,
        _SAMPLE_RATE,
        format=fmt,
        subtype=subtype,
    )
    return buf.getvalue()


class TestDetectFormatByMagic:
    """Pin `_detect_format` magic-byte mapping against real files and sourced magic."""

    @pytest.mark.parametrize(
        ("fmt", "subtype", "expected"),
        [
            ("wav", None, "wav"),
            ("flac", None, "flac"),
            ("ogg", "vorbis", "ogg"),
            ("mp3", None, "mp3"),
        ],
    )
    def test_detects_generated_formats(self, fmt, subtype, expected):
        """A real file of each supported format must be detected by magic bytes."""
        assert loader._detect_format(_snippet(fmt, subtype), None) == expected

    @pytest.mark.parametrize("sync_bytes", _MPEG_SYNC_HEADERS)
    def test_mp3_mpeg_sync_variants(self, sync_bytes):
        """Any MPEG-1/2/2.5 frame sync is recognized as mp3."""
        # `\x90\x00` merely pads the header to 4 bytes (the `len(data) >= 4`
        # gate); only the leading sync bytes are significant to detection.
        assert loader._detect_format(sync_bytes + b"\x90\x00", None) == "mp3"

    def test_mp3_id3_tag(self):
        """Files carrying an ID3v2 tag header are recognized as mp3."""
        assert loader._detect_format(b"ID3\x04\x00\x00", None) == "mp3"

    @pytest.mark.parametrize("atom", _RECOGNIZED_FTYP_ATOMS)
    def test_m4a_recognized_ftyp_atom(self, atom):
        """An M4A `ftyp` atom of a recognized leading size is detected."""
        assert loader._detect_format(atom, None) == "m4a"

    def test_m4a_other_first_atom_not_recognized(self):
        """An M4A `ftyp` atom of an unrecognized leading size is missed.

        Only `0x18`/`0x1c`/`0x20` at offset 0 count as m4a (MP4 box sizes are
        variable); a valid `0x24` first atom is not recognized. Pins current
        behavior — candidate for hardening.
        """
        assert loader._detect_format(_UNRECOGNIZED_FTYP_ATOM, None) is None

    @pytest.mark.parametrize("size", M4A_LEADING_SIZES)
    def test_m4a_leading_size_without_ftyp_is_misdetected(self, size):
        """Any data whose first 4 bytes match a known M4A leading size is classed m4a.

        Detection keys only on the big-endian size at offset 0 and never checks
        the `ftyp` type string at bytes 4-7, so a leading size present in
        `M4A_LEADING_SIZES` matches even with a non-`ftyp` payload. Pins current
        behavior — candidate for hardening.
        """
        assert loader._detect_format(size + b"junk", None) == "m4a"


class TestDetectFormatByFilename:
    """Pin `_detect_format` filename-extension fallback when magic is unknown."""

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("clip.mp3", "mp3"),
            ("clip.WAV", "wav"),
            ("clip.m4a", "m4a"),
        ],
    )
    def test_filename_fallback_recognized(self, filename, expected):
        """Unknown magic falls back to a recognized extension (lowercased)."""
        assert loader._detect_format(_UNKNOWN_MAGIC, filename) == expected

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("clip.bin", None),
            ("clip", None),
        ],
    )
    def test_filename_fallback_unrecognized(self, filename, expected):
        """Unknown magic with no recognized extension falls back to None."""
        assert loader._detect_format(_UNKNOWN_MAGIC, filename) == expected


class TestDetectFormatPrecedence:
    """Pin that magic bytes win over a conflicting filename extension."""

    def test_magic_bytes_take_precedence_over_filename(self):
        """A recognized magic header wins even against a conflicting extension."""
        assert loader._detect_format(b"RIFFxxxx", "clip.mp3") == "wav"


class TestLoadAudioGuard:
    """Verify `load_audio` rejects unsupported formats and decodes known ones."""

    @pytest.mark.parametrize("fmt", ["wav", "mp3"], ids=["wav", "mp3"])
    def test_generated_decodes(self, fmt):
        """A generated {fmt} clip must round-trip through detection and decode.

        Either route must yield a valid mono float32 array.
        """
        # MP3 specifically can trip libsndfile's in-memory `BytesIO` path in some
        # builds/versions; `load_audio` then falls back to a temp-file path-decode.
        mono, sr = loader.load_audio(_snippet(fmt), target_sr=_SAMPLE_RATE)

        assert mono.dtype == np.float32
        assert mono.ndim == 1
        assert mono.shape[0] > 0
        assert np.all(np.isfinite(mono))
        assert sr == _SAMPLE_RATE

    @pytest.mark.parametrize(
        ("data", "kwargs"),
        [
            (_UNKNOWN_MAGIC, {}),
            (_UNKNOWN_MAGIC, {"filename": "clip.bin"}),
        ],
    )
    def test_unsupported_input_raises(self, data, kwargs):
        """Bytes with no recognizable magic/extension must raise before decoding."""
        with pytest.raises(AudioProcessingError):
            loader.load_audio(data, **kwargs)

    def test_stereo_wav_downmixes_to_mono(self):
        """Multichannel input averages channels into a mono array."""
        left = np.zeros(_FRAMES, dtype=np.float32)
        right = np.ones(_FRAMES, dtype=np.float32)
        stereo = np.stack([left, right], axis=1)  # (frames, 2) -> 2-channel
        # FLOAT subtype keeps 0.0/1.0 exact: default PCM wav quantizes 1.0 to
        # 32767/32768, skewing the mean to ~0.49998.
        mono, sr = loader.load_audio(
            _snippet("wav", subtype="FLOAT", data=stereo), target_sr=_SAMPLE_RATE
        )

        assert mono.ndim == 1
        assert sr == _SAMPLE_RATE
        assert mono == pytest.approx(0.5, abs=1e-6)
