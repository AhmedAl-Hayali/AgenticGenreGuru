# Implementation Plan: Song Fingerprint Engine

**Branch**: `001-song-fingerprint-engine` | **Date**: 2026-08-03 | **Spec**: [spec.md](spec.md)

**Input**: User explicit choices: Python, PostgreSQL, Django frontend, SQLAlchemy backend ORM, librosa/numpy/scipy audio DSP, Deezer API for audio snippets, 2-click song match confirmation UI.

## Summary

Build GenreGuru Song Fingerprint Engine using a modular Python architecture. Django serves the frontend UI featuring a song search bar and candidate match list with 2-click selection/confirmation UX. The backend core utilizes a standalone Python library structure with Deezer API integration for online audio snippet retrieval, librosa/numpy/scipy for digital signal processing (spectral centroid, etc.), and SQLAlchemy for PostgreSQL database persistence.

## Technical Context

**Language/Version**: Python 3.14 (in accordance with [pyproject.toml](../../pyproject.toml))

**Primary Dependencies**: Django (frontend), SQLAlchemy & psycopg (backend DB), librosa, numpy, scipy (audio DSP: `spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, `mfcc`), httpx (Deezer API), rich (terminal/RichHandler console), hydra-core + OmegaConf (configuration management)

**Dev & Pre-commit Tooling**: Bandit (security audit), Radon (code metric & complexity analysis), FactoryBoy (`factory_boy` for integration test fixtures), pytest, pytest-django, pytest-mock, pytest-cov (test coverage analysis), ruff (linting & formatting via `ruff check`/`ruff format`), ty (type-checking), prek (pre-commit hooks framework)

**Storage**: PostgreSQL (local relational database)

**Testing**: pytest, pytest-django, pytest-mock, factory_boy, pytest-cov

**Target Platform**: Web application (Django web interface + Python DSP core)

**Project Type**: Web application (Django frontend + standalone Python core library & services)

**Performance Goals**: Audio feature extraction completion <10s per snippet; DB feature lookup <500ms.

**Constraints**: Network retry (3x, 5s delay) on snippet fetch failures; error handling for unprocessable audio; support MP3, WAV, FLAC. PostgreSQL 18+ required — all `UUID` columns rely on the native `uuidv7()` function as the column default with no application-layer fallback (data-model.md). Current Deezer integration is user-independent (30s previews only); future scope plans `deezer-python` and multi-provider auth (Spotify, YouTube Music, Apple Music, Amazon Music) for user library access. V1 downsamples temporal feature vectors into single scalar values per feature.

**Scale/Scope**: Top 5 match candidates display, 2-click selection UI, 19 EARS-compliant functional requirements.

## Constitution Check

*GATE: Passed*

- **I. Standalone Library-First Architecture**: Core audio fetcher, DSP feature extractor, and database repositories implemented as decoupled Python modules independent of Django UI views.
- **II. XP & Incremental Iteration**: Implementation split into small, testable modules (Deezer client → Audio DSP → SQLAlchemy models → Django UI).
- **III. Strict TDD**: Red-Green-Refactor enforced across all unit and integration tests.
- **IV. Simplicity & Modular Adaptability**: Clean interfaces between Deezer API client, DSP engine, and database layer.
- **V. SOLID**: Single Responsibility per service component (fetcher, extractor, repo, UI controller).

## Project Structure & Architecture Justification

### Documentation (this feature)

```text
specs/001-song-fingerprint-engine/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── contracts/           # Phase 1 output (/speckit-plan command)
    ├── deezer-api.md
    └── search-api.md
```

### Source Code Structure

```text
config/                    # Hydra config tree (config.yaml defaults + config groups)
├── config.yaml            # defaults: - logging: dev, - db: dev, - features: default, - django: dev, - _self_
├── logging/               # dev.yaml / prod.yaml (logging group; see logging-report.md)
├── db/                    # dev.yaml / prod.yaml (db group; secrets via ${oc.env:...})
├── features/              # default.yaml / all.yaml (visualization + recommendations flags)
└── django/                # dev.yaml / prod.yaml (web-layer settings; selected via GENREGURU_ENV)
src/
├── genreguru/
│   ├── audio/           # librosa/numpy/scipy DSP feature engineering
│   ├── deezer/          # Deezer API client & retry logic
│   ├── db/              # SQLAlchemy models, engine, & repositories
│   ├── config.py        # Hydra compose helper (Django path)
│   ├── gglogging.py     # dictConfig setup, JsonFormatter, NonErrorFilter, QueueHandler (logging-report.md)
│   ├── errors.py        # shared exception hierarchy (NetworkDisconnectedError, AudioProcessingError, ...)
│   ├── fingerprint_service.py  # US1 orchestration (ISRC reuse, fetch → extract → store)
│   └── recommendations.py      # US4 RecommendationService (cosine similarity over 8-dim vectors)
frontend/                # Django web application
├── genreguru_web/       # Django project settings & URL routing
├── fingerprint_app/     # Django app (views, templates, static JS/CSS)
│   ├── templates/
│   │   └── fingerprint_app/
│   │       └── index.html
│   └── views.py
tests/
├── unit/                # Core DSP, Deezer client, and model unit tests
├── integration/         # DB integration & Deezer retry tests (with FactoryBoy)
├── contract/            # Search & fingerprint contract tests
└── benchmarks/          # SC-002 (<10s extraction) & SC-005 (<500ms ISRC reuse) benchmarks
```

> **Configuration management**: all non-secret settings (logging handler config, DB connection) live in the Hydra `config/` tree and are overridable from the CLI; secrets resolve via `${oc.env:...}` interpolation. Standalone scripts use `@hydra.main`; the Django app uses the compose API via `genreguru/config.py`. See [config-report.md](../../docs/001-song-fingerprint-engine/config-report.md).

### Subdirectory Architecture Justification

#### 1. Why `src/` is subdivided into `genreguru/audio/`, `genreguru/deezer/`, and `genreguru/db/`:
- **`genreguru/audio/` (DSP Feature Extraction)**: Encapsulates pure mathematical signal processing code (librosa, numpy, scipy). Isolating signal processing into its own subpackage ensures DSP algorithms can be developed, optimized, and unit-tested in isolation without dependencies on database connections or HTTP networking.
- **`genreguru/deezer/` (External API Client & Retry)**: Encapsulates network operations, HTTP transport, and Deezer-specific API error handling (`NetworkDisconnectedError`). Keeping external network clients separate from local DSP code isolates network volatility and simplifies mocking network responses during testing.
- **`genreguru/db/` (SQLAlchemy ORM & Persistence)**: Houses PostgreSQL database schemas, SQLAlchemy engine initialization, and repository pattern access functions. Repository functions persist both the track ISRC and the platform track ID (Deezer track ID) for every processed song and implement deduplication lookups that match existing songs by ISRC; if no local record matches the ISRC, they generate and store a new fingerprint. Separating persistence from DSP logic guarantees that audio features can be computed without mandating database writes (e.g. for transient preview testing).

#### 2. Why `frontend/` is subdivided into `genreguru_web/` and `fingerprint_app/`:
- **`frontend/genreguru_web/` (Django Project Root)**: Follows standard Django framework conventions by isolating project-level configurations (`settings.py`), root URL dispatchers (`urls.py`), and WSGI/ASGI entrypoints (`wsgi.py`, `asgi.py`). This manages application-wide middleware and global setup.
- **`frontend/fingerprint_app/` (Django Application Module)**: Contains application-specific controllers (`views.py`), templates (`templates/fingerprint_app/index.html`), and static UI assets. Grouping feature-specific views and templates into a dedicated Django app allows clean modular growth as additional web features (such as user management or recommendation views) are added.

### Architectural Trade-offs & Alternatives

| Layout Strategy                                                                                               | Pros                                                                                                                                                      | Cons                                                                                                                                         | Decision Rationale                                                                                             |
|---------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| **Selected Layout** (`src/` core + `frontend/` Django app)                                                    | High modularity, headless CLI capability, independent unit testing of DSP engine without Django boilerplate, clean boundary for future service extraction | Requires explicit `sys.path` / package import wiring between Django views and `src/` module                                                  | Chosen. Strictly upholds Constitution Principle I while keeping single `pyproject.toml` repository simplicity. |
| **Alternative A: Monolithic Django App** (All logic inside `frontend/fingerprint_app/`)                       | Standard Django conventions, single package layout, simplest import paths                                                                                 | Couples audio DSP and SQLAlchemy models to Django framework lifecycle; prevents reusing DSP core in standalone scripts; violates Principle I | Rejected due to framework coupling and architectural rigidity.                                                 |
| **Alternative B: Multi-Package Monorepo** (`packages/core` + `apps/web` with separate `pyproject.toml` files) | Strictest dependency isolation; independent package publishing and versioning                                                                             | Complex tooling setup (workspace management, dual environment builds, multi-package lockfiles)                                               | Rejected as over-engineering for current project scope.                                                        |

## Complexity Tracking

| Violation                              | Why Needed                                                                      | Simpler Alternative Rejected Because                                      |
|----------------------------------------|---------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| Dual ORM (SQLAlchemy backend + Django) | User explicitly specified Django frontend and SQLAlchemy backend DB interfacing | Direct Django ORM would couple core DSP library to Django framework state |
