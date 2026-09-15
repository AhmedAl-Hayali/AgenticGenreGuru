# ADR-0013: Logging to stdout in production via `prod.yaml`

- **Status**: Accepted
- **Date**: 2026-09-14

## Context

Production logging previously wrote to `logs/genreguru.log.jsonl` via a
`SafeRotatingFileHandler` in `config/logging/prod.yaml`. In containerized
deployments (Docker, PaaS), this file lives on an ephemeral path — lost
on container stop, invisible to `docker logs`, and requiring volume
management or log-rotation configuration.

The 12-factor app methodology treats logs as event streams: all services
should write to stdout/stderr, letting the execution environment
(hypervisor, container runtime, PaaS) handle aggregation and retention.

## Decision

Remove the `file_all` handler from `config/logging/prod.yaml`. The
production logging config writes exclusively to stdout and stderr. No
file-based handler exists. The `prod-docker.yaml` variant is deleted
since `prod.yaml` itself now suffices for both Docker and non-Docker
deployments.

## Consequences

- `docker logs` captures all application logs without additional
  configuration.
- No ephemeral log file to manage — no volume mounts, no log rotation
  policies, no log drift across replicas.
- Non-Docker PaaS platforms (Fly.io, Render, Railway) also consume
  stdout, so the same config works everywhere.
- Structured JSON logging via `genreguru.gglogging.JsonFormatter` is
  removed from `prod.yaml`. If structured logging is needed in the
  future, it can be added via a logging driver or sidecar rather than
  writing to a file inside the container.
- The `LOGGING_GROUP` env var override in `runtime.py` is removed —
  `get_config()` always loads the `prod.yaml` logging group.

## References

- `config/logging/prod.yaml` — updated to stdout-only handlers
- `config/logging/prod-docker.yaml` — deleted
- `docs/ROADMAP.md` Infrastructure — open question: "pick stdout-only
  override vs mounted volume"
