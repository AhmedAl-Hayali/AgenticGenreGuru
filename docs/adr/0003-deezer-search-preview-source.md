# ADR-0003: Use Deezer public search + 30 s previews (V1 source)

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

V1 needs a track-search + short-audio-preview source with no OAuth.
Evaluated Spotify (OAuth + mostly dead previews) and YouTube Data (API
keys + extraction overhead).

## Decision

Use the Deezer public API (`/search`, `/track/{id}`) and its 30-second
MP3 previews as the V1 catalog/preview source.

## Consequences

- No OAuth for V1; preview MP3s are sized well under the <10 s DSP target.
- Catalog and preview coverage are bounded by Deezer (known limitation:
  single-provider dependency, preview length).
- Future multi-provider path reserved (`deezer-python` OAuth later).

## References

- [`docs/ARCHITECTURE.md §8`](../ARCHITECTURE.md); `contracts/deezer-api.md`;
  `docs/ROADMAP.md` (planned multi-provider).