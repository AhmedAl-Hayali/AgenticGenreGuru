# Quickstart & Validation Guide: Song Fingerprint Engine

## Prerequisites

- Python 3.14+
- PostgreSQL database running locally
- Node.js 26+ and npm (for the frontend JS toolchain)
- Virtual environment with dependencies (`django`, `sqlalchemy`, `psycopg2-binary`, `librosa`, `numpy`, `scipy`, `httpx`, `pytest`)

## Setup

Configuration is driven by Hydra config groups in `config/` (see [config-report.md](../../docs/001-song-fingerprint-engine/config-report.md)). The dev database group is the default:

```bash
# Optional: override the dev DB connection (secrets resolved via ${oc.env:...}, never committed)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/genreguru"

# Run database migrations / table creation script (Hydra loads config automatically)
python -m genreguru.db.init_db
```

Switch environments or settings from the command line without editing files:

```bash
python -m genreguru.db.init_db db=prod                 # use config/db/prod.yaml
python -m genreguru.db.init_db logging.level=DEBUG     # any config key is overridable
```

## Running the Application

```bash
# Start Django dev server
python frontend/manage.py runserver 0.0.0.0:8000
```

Open browser to `http://localhost:8000`.

## Frontend JS Toolchain

The browser UI source of truth is `frontend/fingerprint_app/ts/` — reusable modules (`dto`, `config`, `api`, `messages`, `render`, `page-controller`, `errors`) plus a thin per-page bootstrap (`ts/pages/index-page.ts`). esbuild bundles the bootstrap to the served ES module `frontend/fingerprint_app/static/fingerprint_app/app.js` — a generated, gitignored artifact, so a fresh checkout must run `npm run build` before `runserver` or any `collectstatic` deploy. The source is checked by ESLint 10 (flat config, `eslint.config.ts`), formatted with Prettier 3, typechecked with `tsc` (strict, no emit), and unit-tested with Vitest 5 + jsdom contract tests in `frontend/tests/`.

```bash
cd frontend

# Install the JS toolchain from the lockfile
npm ci

# Build the browser bundle (esbuild)
npm run build

# Full gate: build + lint + format:check + typecheck + unit tests
npm run check
```

All checks run in CI (`tests.yml`, `frontend` job: `npm ci` → `npm run check` (which builds) → `npm run test:coverage` with artifact upload), so they must pass before merge.

## Validation Workflows

### Scenario 1: Search & 2-Click Confirmation
1. Type `Daft Punk` in text field and click **Search**.
2. Verify top 5 candidate matches appear in list.
3. Click match once → verifies UI item enters "Selected" state.
4. Click match second time → confirms selection; initiates Deezer audio fetch + librosa DSP fingerprinting.
5. Verify success response and fingerprint metrics displayed.
6. Re-submit the same song and confirm again → verify the existing fingerprint is reused (matched by ISRC) without creating duplicate database records.

### Scenario 2: Automated Integration Tests

```bash
# Run test suite
pytest tests/
```

### Scenario 3: Frontend JS Checks

```bash
cd frontend
npm run check            # build + eslint + prettier + tsc strict + vitest
npm run build:watch      # rebuild the bundle on change (dev)
npm run test:coverage    # coverage report + 90% threshold gate
```
