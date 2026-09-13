# ADR-0010: Static assets — Whitenoise in-container

- **Status**: Accepted
- **Date**: 2026-09-07
- **Note**: Decision recorded; not yet implemented.

## Context

The esbuild output (`fingerprint_app/static/.../app.js`) is gitignored;
the frontend must build inside the container image, and static files need
serving in prod without an external CDN.

## Decision

Serve static assets via Whitenoise in-container: Node 26 builder stage
(`npm ci && npm run build`) → `collectstatic` → whitenoise.

## Consequences

- No external static host required for V1 deploys.
- Future-proof path stays open: `ManifestStaticFilesStorage`
  cache-busting; object storage/CDN (MinIO/S3) when media/uploads grow.

## References

- `docs/ROADMAP.md` Infrastructure (D3).