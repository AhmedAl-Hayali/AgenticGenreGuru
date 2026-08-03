# EARS Lint Report

- **Slug**: 001-song-fingerprint-engine
- **Linted**: 2026-08-03
- **Source**: `specs/001-song-fingerprint-engine/spec.md`
- **Conformance**: 0 of 11 requirements conform to EARS (0%)

## Findings

| Ref | Verdict | Pattern / Issues | Severity | Suggested EARS Rewrite |
|-----|---------|------------------|----------|------------------------|
| L97 / FR-001 | non-conformant | missing modal (`MUST`); missing trigger; compound requirement | error | When a user inputs a song name, the system shall return the top 5 matching candidates from online catalog sources and await user confirmation. |
| L98 / FR-002 | non-conformant | missing modal (`MUST`); missing trigger; weak verb "supporting" | error | When the user confirms a song match, the system shall fetch an online audio snippet in MP3, WAV, or FLAC format prior to feature extraction. |
| L99 / FR-003 | non-conformant | missing modal (`MUST`); missing trigger; compound requirement | error | When an audio snippet is fetched, the system shall compute individual acoustic features including spectral centroid and spectral flux and group them into a single song feature vector. |
| L100 / FR-004 | non-conformant | missing modal (`MUST`); missing trigger | error | When a song feature vector is generated, the system shall store the feature vector in the local relational database. |
| L101 / FR-005 | non-conformant | missing modal (`MUST`); missing trigger/state | error | When storing a fingerprint record, the system shall associate the record with song title, audio source reference, and processing timestamp. |
| L102 / FR-006 | non-conformant | missing modal (`MUST`); informal event structure | error | When a user submits a song that is already fingerprinted in the database, the system shall reuse the existing fingerprint record without creating a duplicate entry. |
| L103 / FR-007 | non-conformant | missing modal (`MUST`); weak verb "handle"; compound requirement | error | If a network interruption occurs during audio snippet fetching, then the system shall retry fetching up to 3 times with 5-second delays between attempts; if all 3 retries fail, then the system shall display a "network disconnected" error message. |
| L104 / FR-008 | non-conformant | missing modal (`MUST`) | error | If fetched audio data fails digital signal processing, then the system shall display an "audio file cannot be processed" error message. |
| L105 / FR-009 | non-conformant | missing modal (`MUST`); missing trigger | error | When a user requests stored fingerprint details, the system shall retrieve and display the fingerprint feature record from the local relational database. |
| L106 / FR-010 | non-conformant | missing modal (`MAY`); missing trigger | error | Where DSP visualization is enabled, when a user selects a fingerprinted song, the system shall display the spectrogram with highlighted spectral centroid and feature contribution factors. |
| L107 / FR-011 | non-conformant | missing modal (`MAY`); missing trigger | error | Where custom recommendation querying is enabled, when a user modifies acoustic feature vector values, the system shall retrieve song recommendations matching the modified feature vector. |

## Summary

- **Errors**: 11
- **Warnings**: 2 (weak verbs: "supporting", "handle")
- **Info**: 0
- **Top Recurring Issues**:
  1. Missing mandatory `shall` modal (used `MUST` or `MAY` throughout).
  2. Missing EARS trigger keywords (`When`, `While`, `If`, `Where`).
  3. Compound requirements combining multiple distinct actions into single statements.

## Suggested Next Step

Run `/speckit-ears-convert` to apply these EARS-conformant rewrites to `specs/001-song-fingerprint-engine/spec.md`.
