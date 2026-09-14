# Quickstart & Validation Guide

What you get: type a song title → GenreGuru searches the Deezer catalog, shows
top-5 matches, fetches a 30s preview, extracts 8 acoustic features, stores the
fingerprint in PostgreSQL, and reuses it on re-submit.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the developer workflow
(hooks, lint, commit conventions). This file is the end-user path.

## Prerequisites

- **Python 3.14+** with [uv](https://docs.astral.sh/uv/) (project manager)
- **PostgreSQL 18** running locally
- **Node.js 26+** + npm (only needed if you rebuild the frontend bundle)

## Setup

Install dependencies and initialize the database. The dev DB group is the
default; secrets resolve via `${oc.env:DB_*}` (never committed).

```bash
# install python + frontend toolchain (lockfile-pinned)
uv sync --all-extras --dev
npm ci --prefix web

# optional: override dev DB connection (defaults: postgres/postgres@localhost:5432/genreguru)
export DB_USER="postgres"
export DB_PASSWORD="postgres"
export DB_HOST="localhost"
export DB_PORT="5432"

# create schema (Hydra loads config automatically)
uv run python -m genreguru.db.init_db
```

PowerShell equivalent:

```powershell
uv sync --all-extras --dev
npm ci --prefix web
$env:DB_USER="postgres"; $env:DB_PASSWORD="postgres"; $env:DB_HOST="localhost"; $env:DB_PORT="5432"
uv run python -m genreguru.db.init_db
```

Override any config key from the CLI — no file edits needed:

```bash
uv run python -m genreguru.db.init_db db=prod              # config/db/prod.yaml
uv run python -m genreguru.db.init_db logging.level=DEBUG
```

## Run

```bash
uv run python web/manage.py runserver 0.0.0.0:8000
```

Open [http://localhost:8000](http://localhost:8000).

## Try it

1. Type a song title (e.g. `Harder, Better, Faster, Stronger` by Daft Punk), click **Search**.
2. Pick from the top-5 matches — click once to select, click again to confirm.
3. GenreGuru fetches the 30s preview, fingerprints it, and stores it.
4. Re-submit the same song → existing fingerprint is reused (ISRC dedup, no duplicate).

## Validation

```bash
# backend test suite
uv run pytest tests/

# frontend gate: build + eslint + prettier + tsc strict + vitest
npm run --prefix web check

# frontend coverage (95% threshold gate; HTML + LCOV in web/coverage/)
npm run --prefix web test:coverage
```

All of the above run in CI (`tests.yml`); they must pass before merge.