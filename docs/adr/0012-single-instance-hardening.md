# ADR-0012: Scale/hardening — single instance, standard hardening

- **Status**: Accepted
- **Date**: 2026-09-07
- **Note**: Decision recorded; not yet implemented.

## Context

Prod settings already enforce `DEBUG=0`, secure cookies, HSTS, and
fail-closed `DJANGO_ALLOWED_HOSTS`/`DJANGO_SECRET_KEY`/`DB_*` via env. A
TLS-terminating reverse proxy needs the proxy-header signal or the
`secure_ssl_redirect` would loop.

## Decision

Run a single instance with standard hardening. Add
`SECURE_PROXY_SSL_HEADER` for the TLS-terminating proxy; rate-limiting
(CHK024) stays deferred.

## Consequences

- Correct TLS handling behind the proxy on first deploy.
- Future path reserved: multi-replica, WAF/ingress, secrets manager, and
  `CONN_MAX_AGE`/pool tuning per replica.

## References

- `docs/ROADMAP.md` Infrastructure (D5).