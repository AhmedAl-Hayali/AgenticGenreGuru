# GenreGuru

![Python](https://img.shields.io/badge/Python-3.14%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1%2B-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18%2B-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Coverage (Python)](https://img.shields.io/codecov/c/github/AhmedAl-Hayali/AgenticGenreGuru.svg?flag=pytest&label=Python%20coverage&style=for-the-badge&logo=codecov&logoColor=white)
![Coverage (TypeScript)](https://img.shields.io/codecov/c/github/AhmedAl-Hayali/AgenticGenreGuru.svg?flag=vitest&label=TypeScript%20coverage&style=for-the-badge&logo=codecov&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL--3.0-green?style=for-the-badge)

**GenreGuru** turns a song title into a machine-readable acoustic fingerprint. Type a title → it pulls a 30-second Deezer preview → runs a DSP pipeline extracting 8 acoustic features → stores the vector in PostgreSQL. Recommending sonically similar tracks by querying stored fingerprints with cosine similarity is planned (US4).

## Table of Contents

- [Project Status](#project-status)
- [What GenreGuru Does](#what-genreguru-does)
- [How It Works](#how-it-works)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Learn More](#learn-more)
- [License](#license)

## Project Status

Partial implementation. Phase 1 core library + US1 search/confirm implemented; docs navigation skeleton shipped (2026-09-13); frontend preview UX in flight; deployment (D1–D5) designed, not implemented. Still pending: DSP visualization (US3), custom recommendations (US4), benchmarks, and end-to-end runs against a live PostgreSQL. See [`specs/001-song-fingerprint-engine/tasks.md`](specs/001-song-fingerprint-engine/tasks.md) for the implementation plan.

**Progress:** Phase 1 complete (core library + API endpoints + docs skeleton). Phase 2 pending (DSP viz, recommendations, benchmarks, end-to-end runs).

**Known Limitations:**  
_These constraints are tracked in the roadmap and will be addressed in future phases._
- **30-second previews only** — Deezer API provides 30-second audio snippets, not full tracks. Fingerprints are based on this limited window.
- **Deezer catalog dependency** — Song search and audio previews depend on Deezer's API availability and catalog coverage.
- **No genre classification** — GenreGuru extracts acoustic features, not genre labels. It finds sonically similar tracks, not genre-matched ones.

## What GenreGuru Does

GenreGuru takes a song title as input and produces a compact acoustic fingerprint — a numerical signature that captures the sonic character of a track. It searches the Deezer catalog, fetches a 30-second audio preview, runs it through a DSP pipeline that extracts 8 key acoustic features, and stores the result locally for later analysis.

**Built for:**
- **Music producers** — Compare your track's sonic profile against a growing library
- **Audio engineers** — Inspect spectral characteristics of reference tracks
- **Music theorists** — Analyze acoustic features across genres and eras
- **Music educators** — Demonstrate DSP concepts with real audio
- **Hobbyist musicians** — Discover songs with similar sonic fingerprints
- **Casual listeners** — Explore music through its acoustic properties

## How It Works

```mermaid
flowchart TD
    U[/"Search: song title"/] --> SEARCH["Search Deezer API"]
    SEARCH --> RESULTS["Top 5 matches"]
    RESULTS --> CONFIRM["User confirms selection"]
    CONFIRM --> LOOKUP{"ISRC exists locally?"}
    LOOKUP -->|"Yes"| REUSE["Return stored fingerprint"]
    LOOKUP -->|"No"| FETCH["Fetch 30s audio preview"]
    FETCH --> DSP["Extract 8 acoustic features"]
    DSP --> STORE["Store fingerprint + metadata"]
    STORE --> DONE[/"Fingerprint returned"/]
    REUSE --> DONE
```

1. **Search** — You type a song title. GenreGuru queries the Deezer API and shows the top 5 matches.
2. **Confirm** — Click once to select, click again to confirm. Two clicks, no mistakes.
3. **Dedup check** — GenreGuru checks if this song already exists in your local database (matched by ISRC). If it does, the stored fingerprint is returned instantly.
4. **Fetch & fingerprint** — If it's new, the 30-second audio preview is fetched, converted to mono, and processed through the DSP pipeline. Eight acoustic features are extracted and collapsed into a single scalar each (future versions may keep MFCC frames as more scalars).
5. **Store** — The fingerprint and song metadata are persisted to PostgreSQL. Re-submitting the same song reuses the stored data.

## Features

- **Song search** — Search by title, select from top 5 candidates with a 2-click confirmation UX. (Search + confirm API and 2-click browser UI implemented; covered by Vitest DOM contract tests in `web/tests/`.)
- **Acoustic fingerprinting** — Extracts 8 features capturing brightness (spectral centroid), energy (RMS), bandwidth, contrast, noisiness (spectral flatness), rolloff, timbre (MFCC), and harmonic content (zero crossing rate).
- **Database persistence** — Stores fingerprints with full song metadata in PostgreSQL.
- **ISRC-based deduplication** — Prevents duplicate records. Reuses stored fingerprints automatically.
- **Network resilience** — Retries audio snippet fetch up to 3 times with 5-second delays on failure.
- **DSP visualization** *(optional)* — Renders spectrograms with highlighted spectral centroid and top contributing features.
- **Custom recommendations** *(optional)* — Adjust acoustic feature sliders to find songs matching a modified fingerprint vector.

## Quick Start

### Prerequisites

- Python 3.14+
- PostgreSQL 18+ running locally
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 26+ and npm (for the frontend JS toolchain)

### Setup

```bash
# Clone the repository
git clone https://github.com/AhmedAl-Hayali/AgenticGenreGuru.git
cd AgenticGenreGuru

# Install dependencies
uv sync

# Install the frontend JS toolchain dependencies (eslint, prettier, vitest, typescript)
cd web
npm ci

# Build the TypeScript browser bundle (esbuild) — the served app.js is a generated artifact
npm run build
cd ..

## Linux / macOS

# Set environment variables
export DB_USER="database-user"
export DB_PASSWORD="database-password"
export DB_HOST="localhost"
export DB_PORT="5432"
# SECRET_KEY is optional for local dev (dev group ships a fallback); required in prod.

# Initialize the database
uv run python -m genreguru.db.init_db

## Windows (PowerShell)

# Set environment variables
$env:DB_USER="database-user"
$env:DB_PASSWORD="database-password"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
# SECRET_KEY is optional for local dev (dev group ships a fallback); required in prod.

# Initialize the database
uv run python -m genreguru.db.init_db
```

### Run

```bash
uv run python web/manage.py runserver 0.0.0.0:8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Validate

1. Type a song title (e.g. `Harder, Better, Faster, Stronger` by Daft Punk) and click **Search**.
2. Verify the top 5 candidate matches appear.
3. Click a match once to select it, click again to confirm.
4. The system fetches the audio snippet, extracts the fingerprint, and stores it.
5. Re-submit the same song — the existing fingerprint is reused (no duplicate).

### Tests

```bash
# Fullstack test suite
uv run pytest

# Core (no Django) test suite
uv run pytest tests/unit tests/integration
```

Frontend checks run the whole toolchain — build (esbuild: TypeScript → minified ESM bundle), lint (ESLint 10 flat config), format (Prettier 3), typecheck (tsc strict on TypeScript sources, no emit), and Vitest 5 DOM contract tests against the TS source (jsdom):

```bash
cd web
npm run check            # build + lint + format:check + typecheck + test in sequence

# Coverage report (HTML + LCOV) written to coverage/; enforces >=95% on all metrics
npm run test:coverage

# Individual tools
npm run build            # esbuild: fingerprint_app/ts/pages/index-page.ts → static/.../app.js (ESM)
npm run build:watch      # rebuild on every change (dev)
npm run lint:check        # ESLint 10 (flat config, eslint.config.ts)
npm run format:write     # Prettier --write (printWidth 100)
npm run typecheck        # tsc --noEmit (strict tsconfig.json on .ts sources)
```

The served `static/fingerprint_app/app.js` is a **generated, gitignored artifact** — the source of truth is the `fingerprint_app/ts/` modules + the per-page `ts/pages/*-page.ts` bootstrap. A fresh `git clone` must run `npm run build` before `runserver`, and any deploy that runs `collectstatic` must execute `npm ci && npm run build` first.

Build, lint, format, typecheck, tests, and coverage are also wired into CI (`tests.yml`, `web` job: `npm run check` + `npm run test:coverage` with artifact upload).

## Architecture

GenreGuru follows a **standalone library-first** architecture. Core components are decoupled from the Django UI and can run independently.

```mermaid
flowchart LR
    subgraph UI_Layer["Django Web UI"]
        UI["Django Views & Templates"]
    end

    subgraph Core["Core Library"]
        API["API routes"]
        DEEZER["Deezer API Client"]
        AUDIO["DSP Feature Extraction"]
        DB["SQLAlchemy + PostgreSQL"]
    end

    UI -->|search / confirm| API
    API --> DEEZER
    API --> DB
    DEEZER -->|"30s audio snippet"| AUDIO
    AUDIO -->|"8 feature scalars"| DB
```

- **`genreguru/audio/`** — Signal processing (librosa, numpy, scipy). Independent of Django.
- **`genreguru/deezer/`** — Deezer API client with retry logic. Isolated for easy mocking.
- **`genreguru/db/`** — PostgreSQL schemas, SQLAlchemy engine, repository pattern.
- **`web/`** — Django views, templates, and static assets. Thin UI layer.

### Data Model

The `songs` and `song_fingerprints` tables are implemented via SQLAlchemy models (`genreguru/db/models.py`), reflecting the schema below.

```mermaid
erDiagram
    SONG ||--o| SONG_FINGERPRINT : "has 1-to-1 fingerprint"

    SONG {
        uuid id PK
        bigint deezer_id UK
        string isrc UK
        string title
        string artist
        string album
        string preview_url
        int duration
        datetime created_at
        datetime updated_at
    }

    SONG_FINGERPRINT {
        uuid id PK
        uuid song_id FK
        float spectral_centroid
        float rms
        float spectral_bandwidth
        float spectral_contrast
        float spectral_flatness
        float spectral_rolloff
        float zero_crossing_rate
        float mfcc
        string audio_format
        int sample_rate
        datetime created_at
        datetime updated_at
    }
```

### API Endpoints

`search` and `confirm` are implemented (Django routes). Catalog, visualization, and recommendation endpoints are pending (`specs/001-song-fingerprint-engine/contracts/search-api.md`).

| Method | Endpoint                           | Description                                                | Status      |
|--------|------------------------------------|------------------------------------------------------------|-------------|
| `GET`  | `/api/search/?query={title}`       | Search songs via Deezer, returns top 5 matches             | Implemented |
| `POST` | `/api/confirm/`                    | Confirm selection, generate or reuse fingerprint           | Implemented |
| `GET`  | `/api/songs/`                      | List all stored songs with fingerprint metadata            | Target      |
| `GET`  | `/api/songs/{isrc}/`               | Get full fingerprint detail for a song                     | Target      |
| `GET`  | `/api/songs/{isrc}/visualization/` | Spectrogram + top-3 factor viz (feature-gated)             | Optional    |
| `POST` | `/api/recommend/`                  | Cosine-similarity top-5 vs modified vector (feature-gated) | Optional    |

## Tech Stack

![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-2.4%2B-013243?style=for-the-badge&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-1.18%2B-8CAAE6?style=for-the-badge&logo=scipy&logoColor=black)
![uv](https://img.shields.io/badge/uv-0.12-DE5FE9?style=for-the-badge&logo=uv&logoColor=black)
![httpx](https://img.shields.io/badge/httpx-0.28%2B-0A0F17?style=for-the-badge)
![librosa](https://img.shields.io/badge/librosa-0.11%2B-0A0F17?style=for-the-badge)
![Node.js](https://img.shields.io/badge/Node.js-26%2B-5FA04E?style=for-the-badge&logo=nodedotjs&logoColor=white)

![esbuild](https://img.shields.io/badge/esbuild-0.28%2B-FFCF00?style=for-the-badge&logo=esbuild&logoColor=black)
![ESLint](https://img.shields.io/badge/ESLint-10-4B32C3?style=for-the-badge&logo=eslint&logoColor=white)
![Prettier](https://img.shields.io/badge/Prettier-3-F7B93E?style=for-the-badge&logo=prettier&logoColor=black)
![Vitest](https://img.shields.io/badge/Vitest-5-6E9F18?style=for-the-badge&logo=vitest&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-9%2B-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-0.16%2B-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)

| Component            | Technology                                            | Why                                                                                   |
|----------------------|-------------------------------------------------------|---------------------------------------------------------------------------------------|
| Language             | Python 3.14                                           | Modern features, type annotation support                                              |
| Web Framework        | Django 6.1+                                           | Mature, well-documented, rapid UI development                                         |
| Database             | PostgreSQL + SQLAlchemy                               | Relational integrity, flexible querying                                               |
| Audio DSP            | librosa, numpy, scipy                                 | Industry-standard audio analysis                                                      |
| HTTP Client          | httpx                                                 | Async-capable, modern replacement for requests                                        |
| Configuration        | Hydra Core                                            | Hierarchical config with CLI overrides                                                |
| Linting              | Ruff                                                  | Fast, comprehensive rule enforcement                                                  |
| Testing              | pytest + pytest-django                                | Django integration, fixtures, coverage                                                |
| Frontend JS          | TypeScript ES modules (source: `fingerprint_app/ts/`) | esbuild bundles a single minified ESM `app.js` per page; type-safe browser code       |
| Frontend Lint/Format | ESLint 10 (flat config) + Prettier 3                  | Enforced style, `eslint-config-prettier` integration                                  |
| Frontend Tests       | Vitest 5 + jsdom + v8 coverage                        | DOM contract tests for the index-page bootstrap (Vitest 5 + jsdom), 95% coverage gate |
| Frontend Types       | TypeScript (strict, no emit)                          | `tsc` typecheck of `.ts` sources                                                      |

## Project Structure

```text
src/        # Standalone core library (import root `genreguru`) — DSP, Deezer client, DB, services
web/        # Django web application — project, app, templates, browser TS source + Vitest tests
config/     # Hydra configuration tree (env groups, feature flags)
tests/      # pytest suites — unit/ integration/ contract/ benchmarks/
specs/      # Feature specifications & design docs → specs/README.md
docs/       # Architecture, API, decision records, roadmap → docs/README.md
```

Each folder's documentation entry point is its `README.md`:
[`docs/README.md`](docs/README.md) indexes all documentation; [`specs/README.md`](specs/README.md) indexes feature specifications.

## Configuration

All non-secret settings live in the Hydra `config/` tree and are overridable from the CLI. Secrets resolve via `${oc.env:...}` interpolation. Django settings (in `genreguru_web/settings/`) contain no environment-specific values — they read the Hydra `django` and `db` groups through `genreguru/config.py`, selected by the `GENREGURU_ENV` variable (`dev` default; `prod` for production). Django and the core library share one DB connection source — the core library uses programmatic URL generation from individual components (`dialect`, `driver`, `user`, `password`, `host`, `port`, `database`) via `genreguru/db/engine.py`, and Django settings are built from the same components (`web/genreguru_web/settings/base.py`).

```bash
# Override any config key from the CLI
uv run python -m genreguru.db.init_db db=prod
uv run python -m genreguru.db.init_db logging.level=DEBUG
```

### Feature Flags

Enable optional features in `config/features/all.yaml` or override at runtime (defaults OFF).

```yaml
visualization:
  enabled: true
recommendations:
  enabled: true
```

## Learn More

Jump to: [`#project-status`](#project-status) · [`#what-genre-guru-does`](#what-genreguru-does) · [`#how-it-works`](#how-it-works) · [`#features`](#features) · [`#quick-start`](#quick-start) · [`#architecture`](#architecture) · [`#data-model`](#data-model) · [`#api-endpoints`](#api-endpoints) · [`#tech-stack`](#tech-stack) · [`#project-structure`](#project-structure) · [`#configuration`](#configuration)

- [`docs/README.md`](docs/README.md) — Documentation index (architecture, API, decision records, roadmap)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Project architecture
- [`docs/API.md`](docs/API.md) — API reference guide and API contracts
- [`docs/adr/index.md`](docs/adr/index.md) — Architecture decision records
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Idea backlog and roadmap
- [`docs/docstring-style-guide.md`](docs/docstring-style-guide.md) — Docstring conventions enforced by Ruff and rendered by pdoc
- [`specs/README.md`](specs/README.md) — Feature specifications and design docs
- **Live API Reference** — pdoc-deployed API reference on GitHub Pages (generated from `genreguru` docstrings via `uv run pdoc`)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributing guide
- [`SECURITY.md`](SECURITY.md) — security policy
- [`CHANGELOG.md`](CHANGELOG.md) — changelog

## License

[GNU Affero General Public License v3.0](LICENSE)

## Author

Ahmed Al-Hayali
