# ADR-0005: Hydra + OmegaConf for configuration

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

All non-secret settings need a hierarchical, overridable home; secrets
must resolve from the environment, not the repo. Options: raw
`os.environ`, bare OmegaConf, argparse defaults, or Hydra.

## Decision

Use Hydra (`hydra-core`) with OmegaConf for configuration: hierarchical
YAML under `config/` with `defaults` groups, CLI overrides, and
`${oc.env:...}` secrets interpolation. Standalone scripts use
`@hydra.main`; the Django path uses the compose API via
`genreguru/config.py`.

## Consequences

- Single source of truth for non-secret settings; secrets never committed.
- Two loading modes to keep straight (Django uses compose, never
  `@hydra.main`).

## References

- [`docs/ARCHITECTURE.md §8`](../ARCHITECTURE.md), `§3.4`; `docs/001-song-fingerprint-engine/config-report.md`.