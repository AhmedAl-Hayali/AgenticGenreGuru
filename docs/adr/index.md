# Architecture Decision Records

Decision log for GenreGuru. One record per decision, numbered
monotonically (see [0000-use-architecture-decision-records](0000-use-architecture-decision-records.md)
for the adopted format and process). New decisions: copy
[adr-template.md](adr-template.md), number it, open a PR.

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0000](0000-use-architecture-decision-records.md) | Use architecture decision records | Accepted | 2026-09-12 |
| [0001](0001-src-core-web-django.md) | `src/` core library + `web/` Django layer | Accepted | 2026-08-17 |
| [0002](0002-sqlalchemy-core-django-orm-web.md) | SQLAlchemy core + Django ORM web (dual ORM) | Accepted | 2026-08-17 |
| [0003](0003-deezer-search-preview-source.md) | Deezer public search + 30 s previews (V1 source) | Accepted | 2026-08-17 |
| [0004](0004-librosa-numpy-scipy-dsp.md) | librosa/numpy/scipy DSP stack | Accepted | 2026-08-17 |
| [0005](0005-hydra-omegaconf-config.md) | Hydra + OmegaConf for configuration | Accepted | 2026-08-17 |
| [0006](0006-confirm-response-shape.md) | `POST /api/confirm/` response shape (no `reused` leak) | Accepted | 2026-08-17 |
| [0007](0007-scalar-collapse-features.md) | Scalar collapse per feature (V1) | Accepted | 2026-08-17 |
| [0008](0008-deploy-local-prod-sim-first.md) | Deploy target: local prod-sim first, cloud later | Accepted | 2026-09-07 |
| [0009](0009-gunicorn-wsgi-sync-workers.md) | App server: Gunicorn (WSGI, sync workers), no `--preload` | Accepted | 2026-09-07 |
| [0010](0010-whitenoise-in-container-static.md) | Static: Whitenoise in-container | Accepted | 2026-09-07 |
| [0011](0011-compose-pg18-migrate-backup.md) | DB reliability: compose PG18 + named volume + healthcheck + migrate job + `pg_dump` | Accepted | 2026-09-07 |
| [0012](0012-single-instance-hardening.md) | Scale/hardening: single instance, standard hardening | Accepted | 2026-09-07 |
| ADR                                               | Title                                                                               | Status   | Date       |
|---------------------------------------------------|-------------------------------------------------------------------------------------|----------|------------|
| [0000](0000-use-architecture-decision-records.md) | Use architecture decision records                                                   | Accepted | 2026-09-12 |
| [0001](0001-src-core-web-django.md)               | `src/` core library + `web/` Django layer                                           | Accepted | 2026-08-17 |
| [0002](0002-sqlalchemy-core-django-orm-web.md)    | SQLAlchemy core + Django ORM web (dual ORM)                                         | Accepted | 2026-08-17 |
| [0003](0003-deezer-search-preview-source.md)      | Deezer public search + 30 s previews (V1 source)                                    | Accepted | 2026-08-17 |
| [0004](0004-librosa-numpy-scipy-dsp.md)           | librosa/numpy/scipy DSP stack                                                       | Accepted | 2026-08-17 |
| [0005](0005-hydra-omegaconf-config.md)            | Hydra + OmegaConf for configuration                                                 | Accepted | 2026-08-17 |
| [0006](0006-confirm-response-shape.md)            | `POST /api/confirm/` response shape (no `reused` leak)                              | Accepted | 2026-08-17 |
| [0007](0007-scalar-collapse-features.md)          | Scalar collapse per feature (V1)                                                    | Accepted | 2026-08-17 |
| [0008](0008-deploy-local-prod-sim-first.md)       | Deploy target: local prod-sim first, cloud later                                    | Accepted | 2026-09-07 |
| [0009](0009-gunicorn-wsgi-sync-workers.md)        | App server: Gunicorn (WSGI, sync workers), no `--preload`                           | Accepted | 2026-09-07 |
| [0010](0010-whitenoise-in-container-static.md)    | Static: Whitenoise in-container                                                     | Accepted | 2026-09-07 |
| [0011](0011-compose-pg18-migrate-backup.md)       | DB reliability: compose PG18 + named volume + healthcheck + migrate job + `pg_dump` | Accepted | 2026-09-07 |
| [0012](0012-single-instance-hardening.md)         | Scale/hardening: single instance, standard hardening                                | Accepted | 2026-09-07 |
| [0013](0013-stdout-only-logging-prod.md)          | Logging to stdout in production via `prod.yaml`                                     | Accepted | 2026-09-14 |