# ADR-0014: Reverse proxy image — `nginx:stable` over `nginx:alpine`

- **Status**: Accepted
- **Date**: 2026-09-14

## Context

The Docker compose setup requires a TLS-terminating reverse proxy
to forward HTTPS requests to the Django Gunicorn application.
`nginx` is the chosen web server for this role. The `nginx:alpine`
image (musl libc) was initially selected for its small footprint.

## Decision

Use `nginx:stable` (Debian-based, glibc) instead of `nginx:alpine`.

## Rationale

Alpine Linux uses musl libc instead of glibc. While nginx itself is
well-supported on Alpine, the stripped-down environment creates
practical debugging problems: no `bash`, `curl`, `wget`, `netstat`,
or `ps` available via `docker exec`. When the reverse proxy needs
to evolve (custom headers, auth modules, TLS debugging, WebSocket
support, rate-limiting), Alpine's minimal toolset makes on-the-fly
diagnosis painful. `nginx:stable` provides full glibc compatibility
and standard Debian tooling for debugging without additional
installation steps.

The tradeoff is a larger image (~100MB vs ~5MB), which is negligible
for a single reverse proxy service.

## Consequences

- `docker exec` into the reverse proxy container gives access to
  `bash`, `curl`, `apt-get` — straightforward TLS debugging, proxy
  testing, and configuration inspection.
- No musl/glibc compatibility issues if third-party nginx modules
  are added in the future.
- Slightly larger image size (~100MB vs ~5MB) — acceptable for a
  single service.
- The `nginx.conf` config at `config/docker/nginx.conf` is
  architecture-agnostic and works identically on both images.

## References

- `compose.yaml` — `reverse-proxy` service uses `image: nginx:stable`
- `config/docker/nginx.conf` — reverse proxy configuration
