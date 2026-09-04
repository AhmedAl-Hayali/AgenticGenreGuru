"""Centralized audio format magic-byte constants with source references.

The literals used by `genreguru.audio.loader` to classify bytes (and the
canonical supported-format names) live here so both `loader.py` and its unit
test share a single authoritative source. Each entry cites the defining spec
name and a live reference URL.

Generated formats are validated against these same constants in
`tests/unit/test_loader.py`.
"""

# Every format `loader._detect_format` can return. This is the single
# canonical source of supported formats: `loader.py` guards the pre-decode
# check against it and validates filename-extension fallbacks against it.
SUPPORTED_FORMATS = frozenset({"wav", "flac", "ogg", "mp3", "m4a"})

# Formats identified by a fixed 4-byte magic literal at offset 0:
# 1. "RIFF" chunk marker; Microsoft RIFF:
# https://learn.microsoft.com/en-us/windows/win32/xaudio2/resource-interchange-file-format--riff-
RIFF_MAGIC = b"RIFF"

# 2. "fLaC" stream marker; FLAC (RFC 9639):
# https://www.rfc-editor.org/rfc/rfc9639.html
FLAC_MAGIC = b"fLaC"

# 3. "OggS" page capture pattern; Ogg framing:
# https://xiph.org/ogg/doc/framing.html
OGG_MAGIC = b"OggS"

# Magic literal -> format name, in detection order. Order is significant:
# `_detect_format` returns the first magic that matches `data[:4]`.
MAGIC_TO_FORMAT = {
    RIFF_MAGIC: "wav",
    FLAC_MAGIC: "flac",
    OGG_MAGIC: "ogg",
}

# MPEG-1/2/2.5 frame sync: an 11-bit `1111 1111 111d` word — `0xFF` first byte,
# top 3 bits of the second byte set (MPEG_SYNC_BYTE + MPEG_SYNC_MASK). Shared
# across MPEG layers and versions. `d` bit is "do-not-care"/"disregard" bit.
#
# The 32-bit frame header opens with an 11-bit "frame sync" field (bits
# 31-21), all set. That spans byte 0 entirely (8 bits → MPEG_SYNC_BYTE = 0xFF)
# plus the top 3 bits of byte 1 (bits 23-21 → MPEG_SYNC_MASK = 0xE0). The mask
# asserts only the sync word, leaving the header's low bits (audio version id,
# layer, bitrate index, sampling rate, ...) free to vary; any second byte with
# its top 3 bits set is a valid frame start. Example: `0xff fb` (MPEG-1 Layer
# II) and `0xff f3` (MPEG-2.5 Layer III) both begin with `1111 1111 111d`.
#   MPEG-1:   ISO/IEC 11172-3 (copyleft PDF).
#   MPEG-2:   ISO/IEC 13818-3.
#   MPEG-2.5: unofficial extension of MPEG-2 with an identical sync word.
#   ISO/IEC 11172-3 PDF:
#     https://csclub.uwaterloo.ca/~pbarfuss/ISO11172-3.pdf
MPEG_SYNC_BYTE = 0xFF
MPEG_SYNC_MASK = 0xE0

# "ID3" tag header that precedes MPEG frames:
#   see the ID3v2 file identifier / tag header.
#   https://id3.org/id3v2.3.0
MPEG_ID3_PREFIX = b"ID3"

# M4A (MP4): only the leading box sizes listed here are treated as M4A
# (variable-size boxes are a known gap).
#
# Every MP4 box header is `[4-byte size][4-byte ASCII type]`. The first box is
# normally `ftyp`, so the detector keys on the big-endian size value at byte 0
# (data[:4] in M4A_LEADING_SIZES) — NOT the "ftyp" string, which lives at
# bytes 4-7 and is never read. The leading sizes are the common ftyp lengths:
# 0x18 (24) = size+type+4 major_brand+4 minor_version+8 (two compatible
# brands); 0x1c (28) / 0x20 (32) add more compatible-brand entries. A legal
# ftyp may be any multiple of 4, so other sizes (e.g. 0x24) are missed unless
# the detector additionally inspects bytes 4-7 for the "ftyp" type.
#   ISO/IEC 14496-12, clause 4.3 File Type Box.
#   Standard page: https://www.mpeg.org/standards/MPEG-4/12/
#   Clause text (2008 ed., identical to ISO/IEC 15444-12:2008):
#     https://cdn.standards.iteh.ai/samples/51533/c8233bd62f144bdda13c99156e984616/ISO-IEC-14496-12-2008.pdf
M4A_LEADING_SIZES = (
    b"\x00\x00\x00\x18",
    b"\x00\x00\x00\x1c",
    b"\x00\x00\x00\x20",
)
