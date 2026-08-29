# GenreGuru

![Python 3.14](https://img.shields.io/badge/python-3.14-blue)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)
![Django](https://img.shields.io/badge/django-6.1+-092E20)

**GenreGuru** turns a song title into a machine-readable acoustic fingerprint. Type a title → it pulls a 30-second Deezer preview → runs a DSP pipeline extracting 8 acoustic features → stores the vector in PostgreSQL. Query stored fingerprints by cosine similarity to find sonically similar tracks.

> **Project status:** Pre-implementation. The project structure, Hydra configuration, and feature specs are in place. Core library modules (`audio/`, `deezer/`, `db/`) and the Django UI are scaffolded but not yet implemented. See [`specs/001-song-fingerprint-engine/tasks.md`](specs/001-song-fingerprint-engine/tasks.md) for the implementation plan.

## What GenreGuru Does

GenreGuru takes a song title as input and produces a compact acoustic fingerprint — a numerical signature that captures the sonic character of a track. It searches the Deezer catalog, fetches a 30-second audio preview, runs it through a DSP pipeline that extracts 8 key acoustic features, and stores the result locally for later analysis.

**Built for:**
- **Music producers** — Compare your track's sonic profile against a growing library
- **Audio engineers** — Inspect spectral characteristics of reference tracks
- **Music theorists** — Analyze acoustic features across genres and eras
- **Music educators** — Demonstrate DSP concepts with real audio
- **Hobbyist musicians** — Discover songs with similar sonic fingerprints
- **Casual listeners** — Explore music through its acoustic properties

## How It Works *(planned)*

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

## Features *(planned)*

- **Song search** — Search by title, select from top 5 candidates with a 2-click confirmation UX.
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

### Setup

```bash
# Clone the repository
git clone https://github.com/AhmedAl-Hayali/AgenticGenreGuru.git
cd AgenticGenreGuru

# Install dependencies
uv sync

## Linux / macOS

# Set environment variables
export DATABASE_URL="postgresql://user:pass@host:port/db"
export SECRET_KEY="django-secret-key"

# Initialize the database
python -m genreguru.db.init_db

## Windows (PowerShell)

# Set environment variables
$env:DATABASE_URL="postgresql://user:pass@host:port/db"
$env:SECRET_KEY="django-secret-key"

# Initialize the database
py -m genreguru.db.init_db
```

### Run

```bash
python frontend/manage.py runserver 0.0.0.0:8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Validate *(planned)*

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

## Architecture *(target design)*

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
- **`frontend/`** — Django views, templates, and static assets. Thin UI layer.

### Data Model *(target design)*

```mermaid
erDiagram
    SONG ||--o| SONG_FINGERPRINT : "has 1-to-1 fingerprint"

    SONG {
        uuid id PK
        int deezer_id UK
        string isrc UK
        string title
        string artist
        string album
        string preview_url
        int duration
        datetime created_at
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
    }
```

### API Endpoints *(target design)*

| Method | Endpoint                     | Description                                      |
|--------|------------------------------|--------------------------------------------------|
| `GET`  | `/api/search/?query={title}` | Search songs via Deezer, returns top 5 matches   |
| `POST` | `/api/confirm/{match}`       | Confirm selection, generate or reuse fingerprint |
| `GET`  | `/api/songs/`                | List all stored songs with fingerprint metadata  |
| `GET`  | `/api/songs/{isrc}/`         | Get full fingerprint detail for a song           |

## Tech Stack

| Component     | Technology              | Why                                            |
|---------------|-------------------------|------------------------------------------------|
| Language      | Python 3.14             | Modern features, type annotation support       |
| Web Framework | Django 6.1+             | Mature, well-documented, rapid UI development  |
| Database      | PostgreSQL + SQLAlchemy | Relational integrity, flexible querying        |
| Audio DSP     | librosa, numpy, scipy   | Industry-standard audio analysis               |
| HTTP Client   | httpx                   | Async-capable, modern replacement for requests |
| Configuration | Hydra Core              | Hierarchical config with CLI overrides         |
| Linting       | Ruff                    | Fast, comprehensive rule enforcement           |
| Testing       | pytest + pytest-django  | Django integration, fixtures, coverage         |

## Project Structure

```text
src/genreguru/              # Standalone core library (import root `genreguru`)
├── audio/                 # DSP: loader, features (Feature enum), feature_extract, feature_collapse
├── deezer/                # Deezer API client & retry logic
└── db/                    # SQLAlchemy models, engine & repositories

frontend/                  # Django web application
├── genreguru_web/         # Project settings, URL routing
└── fingerprint_app/       # Views, templates, static assets

config/                    # Hydra configuration tree
tests/                     # unit/, integration/, contract/, benchmarks/
specs/                     # Feature specifications & design docs
docs/                      # API flow diagrams, config reports
```

## Configuration

All non-secret settings live in the Hydra `config/` tree and are overridable from the CLI. Secrets resolve via `${oc.env:...}` interpolation. Django settings (in `genreguru_web/settings/`) contain no environment-specific values — they read the Hydra `django` and `db` groups through `genreguru/config.py`, selected by the `GENREGURU_ENV` variable (`dev` default; `prod` for production). Django and the core library share one DB connection source — the core library uses programmatic URL generation from individual components (`dialect`, `driver`, `user`, `password`, `host`, `port`, `database`) via `genreguru/db/engine.py`, and Django settings are built from the same components (`frontend/genreguru_web/settings/base.py`).

```bash
# Override any config key from the CLI
python -m genreguru.db.init_db db=prod
python -m genreguru.db.init_db logging.level=DEBUG
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

- [`specs/`](specs/) — Feature specifications, requirements, and design docs
- [`docs/`](docs/) — API flow diagrams, contract references, and configuration reports
- [`docs/docstring-style-guide.md`](docs/docstring-style-guide.md) — Docstring conventions enforced by Ruff and rendered by pdoc

## Known Limitations

- **30-second previews only** — Deezer API provides 30-second audio snippets, not full tracks. Fingerprints are based on this limited window.
- **Deezer catalog dependency** — Song search and audio previews depend on Deezer's API availability and catalog coverage.
- **No genre classification** — GenreGuru extracts acoustic features, not genre labels. It finds sonically similar tracks, not genre-matched ones.

## License

[GNU Affero General Public License v3.0](LICENSE)

## Author

Ahmed Al-Hayali
