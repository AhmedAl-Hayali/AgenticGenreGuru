# ADR-0011: DB reliability — compose PG18 + named volume + migrate job + backup

- **Status**: Accepted
- **Date**: 2026-09-07
- **Note**: Decision recorded; not yet implemented.

## Context

Schema runs on PostgreSQL 18+ (native `uuidv7()` requires it; CI already
pins `postgres:18`). Schema bootstrap must not race matching on-boot
mutations.

## Decision

Local prod-sim uses `compose.yaml` PG18 + named volume + healthcheck, a
one-off `migrate` compose service running
`uv run python -m genreguru.db.init_db`, gated on
`service_completed_successfully`, and `pg_dump` backups.

## Consequences

- Deterministic schema bootstrap; no racing mutations.
- Same `DB_*` env contract applies when swapping to managed Postgres
  (Fly/Render/Neon) or pgbouncer/read-replica later.

## References

- `docs/ROADMAP.md` Infrastructure (D4).