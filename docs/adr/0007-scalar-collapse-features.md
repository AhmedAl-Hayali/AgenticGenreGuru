# ADR-0007: Scalar collapse per feature (V1)

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

The DSP extractor produces per-frame ndarrays per feature. V1 needs a
compact feature space for storage and simple recommendation math; V2 may
retain temporal dynamics.

## Decision

Collapse each feature's raw array to a single scalar via arithmetic mean
per feature (V1). Future versions may keep per-section scalars to retain
temporal dynamics (see ROADMAP: N-section collapse).

## Consequences

- Compact 8-dim vector; simplest recommendation math; spec-mandated REQ-011.
- Temporal dynamics intentionally discarded in V1; the 
  extract/collapse split keeps the raw arrays available for a later
  collapse policy without changing extraction.

## References

- [`docs/ARCHITECTURE.md §8`](../ARCHITECTURE.md), `§4` Design Rules; `docs/ROADMAP.md` (N-section collapse).