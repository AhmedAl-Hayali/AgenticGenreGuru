# ADR-0004: librosa/numpy/scipy DSP stack

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

DSP feature extraction (spectral centroid, RMS, bandwidth, contrast,
flatness, rolloff, ZCR, MFCC) needs a maintained Python audio stack that
handles MP3/WAV/FLAC.

## Decision

Use librosa (with numpy/scipy) and `soundfile`/`audioread` for format
decoding.

## Consequences

- Industry-standard analysis stack with efficient per-frame feature output.
- Rejected alternatives: pyAudioAnalysis (dormant), raw `scipy.io.wavfile`
  (no MP3/FLAC).

## References

- [`docs/ARCHITECTURE.md §8`](../ARCHITECTURE.md); `specs/.../research.md`.