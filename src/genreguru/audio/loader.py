"""Audio snippet loader with mono downmix.

Loads audio bytes into a numpy array, converting multichannel audio to
mono by averaging channels. Validates format before DSP processing.

Module logger: DEBUG source/sample_rate/channels/duration/format +
mono-downmix, ERROR `logger.exception` → `AudioProcessingError`,
lazy `%s` args, never log binary buffer.
"""

import io
import logging
from pathlib import Path

import librosa
import numpy as np
from numpy.typing import NDArray

from genreguru.audio._format_magic import (
    M4A_LEADING_SIZES,
    MAGIC_TO_FORMAT,
    MPEG_ID3_PREFIX,
    MPEG_SYNC_BYTE,
    MPEG_SYNC_MASK,
    SUPPORTED_FORMATS,
)
from genreguru.errors import AudioProcessingError

logger = logging.getLogger(__name__)


def _is_mpeg_sync(header_bytes: bytes) -> bool:
    """True if `header_bytes` starts an MPEG-1/2/2.5 frame (`0xFF` + top-3-bit sync)."""
    return (
        header_bytes[0] == MPEG_SYNC_BYTE
        and (header_bytes[1] & MPEG_SYNC_MASK) == MPEG_SYNC_MASK
    )


def _detect_format(data: bytes, filename: str | None) -> str | None:
    """Best-effort format detection from magic bytes or filename extension."""
    if len(data) >= 4:
        for magic, fmt in MAGIC_TO_FORMAT.items():
            if data[:4] == magic:
                return fmt
        if data[:3] == MPEG_ID3_PREFIX or _is_mpeg_sync(data):
            return "mp3"
        if data[:4] in M4A_LEADING_SIZES:
            return "m4a"
    if filename:
        fmt = Path(filename).suffix.lower().lstrip(".")
        if fmt in SUPPORTED_FORMATS:
            return fmt
    return None


def load_audio(
    data: bytes,
    *,
    target_sr: int = 22050,
    filename: str | None = None,
) -> tuple[np.ndarray, int]:
    """Load audio bytes into a mono float32 numpy array.

    Args:
        data: Raw audio file bytes.
        target_sr: Desired output sample rate (default 22050).
        filename: Optional filename hint for format detection.

    Returns:
        Tuple of (mono_audio, sample_rate).

    Raises:
        AudioProcessingError: If format is unsupported or decoding fails.
    """
    fmt = _detect_format(data, filename)
    logger.debug("detected format=%s filename=%s", fmt, filename)

    if fmt not in SUPPORTED_FORMATS:
        raise AudioProcessingError(
            f"unsupported audio format: {fmt or 'unknown'}",
        )

    try:
        audio, sr = librosa.load(io.BytesIO(data), sr=target_sr, mono=False)
        sr = int(sr)
    except AudioProcessingError:
        raise
    except Exception:
        logger.exception("failed to decode audio data")
        raise AudioProcessingError("audio file cannot be processed") from None

    if audio.ndim == 1:
        mono = audio
        channels = 1
    else:
        channels = audio.shape[0]
        mono: NDArray = audio.mean(axis=0).astype(np.float32)

    duration = len(mono) / sr
    logger.debug(
        "loaded source duration=%.2fs sample_rate=%d channels=%d format=%s mono_downmix=%s",
        duration,
        sr,
        channels,
        fmt,
        channels > 1,
    )

    return mono, sr
