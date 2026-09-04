"""Audio processing: spectrum analysis and acoustic feature extraction.

Pipeline: a 30-second preview is fetched, converted to mono
(`genreguru.audio.loader`), and processed through the DSP pipeline. Eight
acoustic features (spectral centroid, RMS, bandwidth, contrast, flatness,
rolloff, zero-crossing rate, MFCC) are computed as raw per-frame ndarrays
(`genreguru.audio.feature_extract`) and collapsed to a single scalar each
(`genreguru.audio.feature_collapse`). The 8 feature names are centralized
in the `Feature` enum (`genreguru.audio.features`).
"""
