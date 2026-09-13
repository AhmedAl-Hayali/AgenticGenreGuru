# ADR-0002: SQLAlchemy core + Django ORM web (dual ORM)

- **Status**: Accepted
- **Date**: 2026-08-17

## Context

The core library owns persistence but must stay framework-agnostic;
Django needs its own ORM for the web layer. Two ORMs against one database,
over one shared `psycopg` connection pool.

## Decision

Core library uses SQLAlchemy (engine, models, repositories); Django uses
its own ORM within request scope. Both connect through the same
programmatic URL components from the Hydra `db` group. Django owns schema
migrations; SQLAlchemy models are read-only reflections of the
Django-managed tables (no `create_all` in production).

## Consequences

- Deliberate trade-off recorded in `plan.md` Complexity Tracking; keeps the
  core free of Django coupling.
- Two ORM stacks to maintain; single pool config shared via Hydra
  `db.pool_size`/`max_overflow`.

## References

- [`docs/ARCHITECTURE.md §1`](../ARCHITECTURE.md) (Dual ORM Connection
  Strategy); `specs/001-song-fingerprint-engine/plan.md`.