# ADR-0009: App server — Gunicorn (WSGI, sync workers), no `--preload`

- **Status**: Accepted
- **Date**: 2026-09-07

## Context

Views are sync today; `wsgi.py`/`asgi.py` entrypoints both exist and the
ASGI path is unused. `--preload` would share one psycopg3 engine/pool
across forked fds — a fork-safety risk. Gunicorn wheels on Python 3.14 are
a verification point (uvicorn/granian are the fallback).

## Decision

Run Gunicorn (WSGI, sync workers) without `--preload`; per-worker import
runs `runtime.init_runtime()` per process (safe).

## Consequences

- Keeps engine/pool per-process; avoids shared-fd pooling.
- Swap to uvicorn/granian ASGI is the future-proof slot when async views
  land.

## References

- `docs/ROADMAP.md` Infrastructure (D2).