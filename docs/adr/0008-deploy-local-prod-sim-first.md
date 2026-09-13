# ADR-0008: Deploy target — local prod-sim first, cloud later

- **Status**: Accepted
- **Date**: 2026-09-07
- **Note**: Decision recorded; not yet implemented.

## Context

GenreGuru needs a prod-grade deployment. The fastest safe step is a local
production simulation mirroring real wiring before committing to a cloud
provider.

## Decision

Build `Dockerfile` + `compose.yaml` (web + postgres + TLS reverse proxy)
mimicking prod wiring locally via `GENREGURU_ENV=prod` config groups. The
same image later deploys to a PaaS (Fly.io/Render/Railway) behind a GH
Actions build→registry→deploy workflow.

## Consequences

- Local environment exercises the production config path early.
- Deployment target stays swappable; no multi-node changes required to
  move to the cloud.

## References

- `docs/ROADMAP.md` Infrastructure (D1).