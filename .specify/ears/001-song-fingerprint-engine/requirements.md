# Requirements (EARS, converted): Song Fingerprint Engine

- **Slug**: 001-song-fingerprint-engine
- **Converted**: 2026-08-03
- **Source**: `specs/001-song-fingerprint-engine/spec.md`

## Event-Driven

- **REQ-001**: When a user inputs a song name string, the system shall search online catalog sources and return the top 5 matching song candidates.
- **REQ-002**: When top 5 song match candidates are displayed, the system shall await user confirmation before initiating snippet fetching.
- **REQ-003**: When a user confirms a song match selection, the system shall fetch an online audio snippet in MP3, WAV, or FLAC format prior to feature extraction.
- **REQ-004**: When an online audio snippet is fetched, the system shall execute composite feature engineering substeps to compute individual acoustic features including spectral centroid and spectral flux.
- **REQ-005**: When individual acoustic features are computed, the system shall group the acoustic features into a single song feature vector.
- **REQ-006**: When a song feature vector is generated, the system shall store the feature vector in the local relational database.
- **REQ-007**: When storing a fingerprint record in the local relational database, the system shall associate the record with song metadata including song title, audio source reference, and processing timestamp.
- **REQ-008**: When a user submits a song that is already fingerprinted in the local relational database, the system shall reuse the existing fingerprint record without creating duplicate database entries.
- **REQ-012**: When a user requests stored fingerprint details, the system shall retrieve and display the fingerprint feature record from the local relational database.

## Unwanted Behavior

- **REQ-009**: If a network interruption occurs during audio snippet fetching, then the system shall retry fetching up to 3 times with 5-second delays between attempts.
- **REQ-010**: If all 3 snippet fetching retries fail, then the system shall display a "network disconnected" error message to the user.
- **REQ-011**: If fetched audio data fails digital signal processing, then the system shall display an "audio file cannot be processed" error message to the user.

## Optional Features

- **REQ-013**: Where DSP visualization is enabled, when a user selects a fingerprinted song, the system shall display the song spectrogram with highlighted spectral centroid and top feature contribution factors.
- **REQ-014**: Where custom recommendation querying is enabled, when a user modifies acoustic feature vector values for a processed song, the system shall retrieve song recommendations matching the modified feature vector.

## Traceability

| Original | EARS Requirement(s) | Pattern | Notes / Assumptions |
|----------|---------------------|---------|---------------------|
| FR-001 | REQ-001, REQ-002 | Event-Driven | Split: input search vs awaiting confirmation |
| FR-002 | REQ-003 | Event-Driven | Specified format constraints (MP3, WAV, FLAC) |
| FR-003 | REQ-004, REQ-005 | Event-Driven | Split: computing features vs grouping into vector |
| FR-004 | REQ-006 | Event-Driven | Target system explicit |
| FR-005 | REQ-007 | Event-Driven | Metadata association explicit |
| FR-006 | REQ-008 | Event-Driven | Deduplication trigger explicit |
| FR-007 | REQ-009, REQ-010 | Unwanted Behavior | Split: retry loop vs final error display |
| FR-008 | REQ-011 | Unwanted Behavior | Format failure condition explicit |
| FR-009 | REQ-012 | Event-Driven | Query trigger explicit |
| FR-010 | REQ-013 | Optional Feature | Optional feature flag explicit |
| FR-011 | REQ-014 | Optional Feature | Optional feature flag explicit |

## Open Clarifications

None.
