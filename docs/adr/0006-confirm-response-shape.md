# ADR-0006: `POST /api/confirm/` response shape (no `reused` leak)

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

The fingerprint action either reuses a stored fingerprint (ISRC match) or
generates a fresh one. The response shape needed a contract; the choice of
whether the caller is told which path ran affects the client API.

## Decision

`POST /api/confirm/` returns a contracted shape —
`{status, song_id, deezer_id, isrc, fingerprint (vector_length: 8)}` —
and does **not** expose a `reused` flag to the caller. The reuse/fresh
outcome is recorded in logs via `FingerprintContextAdapter` extra.

## Consequences

- Caller stays decoupled from the internal reuse path.
- Reuse/fresh is observable in structured logs for diagnostics.

## References

- [`docs/ARCHITECTURE.md §8`](../ARCHITECTURE.md), `§6.3`; `contracts/search-api.md §2`.