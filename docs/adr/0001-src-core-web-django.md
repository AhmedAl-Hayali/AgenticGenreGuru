# ADR-0001: Use `src/` core library + `web/` Django layer

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

GenreGuru needs a DSP + database core that is independent of the Django
presentation layer so it can be tested and run headless (Constitution I).
Options: a monolithic Django app, a multi-package monorepo, or a single
package with a `src/` core and a thin `web/` Django project.

## Decision

Keep a standalone `genreguru/` core library (import root `genreguru`) in
`src/`, with `web/` as the Django application that shells into the core
through repository/service boundaries. One `pyproject.toml`.

## Consequences

- Core is testable without Django; `web/` stays a thin layer.
- Single package keeps dependency and tooling management simple.
- Core must remain free of Django imports to hold the boundary.

## References

- [`docs/ARCHITECTURE.md §1`](../ARCHITECTURE.md), `§3.1-3.2`; Constitution I.