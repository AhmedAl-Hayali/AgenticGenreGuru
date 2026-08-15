# Phase 0 Research: Song Fingerprint Engine

## Technical Decisions & Rationale

### 1. Audio Snippet Retrieval (Deezer API)

- **Decision**: Use Deezer API (`https://api.deezer.com/search?q={query}`) to search songs and fetch 30-second preview audio snippets (`preview` URL).
- **Current Scope**: User-independent integration. Only retrieves public 30-second preview snippets without user authentication.
- **Future Scope & Evolution**: Future versions may use the `deezer-python` package for user authentication (OAuth) to access personal Deezer libraries. This architecture will extend to other music providers (e.g., Spotify, YouTube Music, Apple Music, Amazon Music) for authenticated user library access.
- **Rationale**: Deezer provides a public, unauthenticated search endpoint returning MP3 audio snippet URLs for tracks without requiring complex OAuth flows.
- **Alternatives Considered**: Spotify API (requires OAuth client credentials and preview URLs are deprecated for many tracks), YouTube Data API (requires API keys and heavy video-to-audio extraction overhead).
- **Retry Strategy**: Implement exponential backoff / fixed 5-second interval retry (3 attempts max) using `urllib3` / `httpx` retry transport.

### 2. Audio Processing & Feature Engineering (librosa / numpy / scipy)

- **Target Runtime**: Python 3.14 (in accordance with `pyproject.toml`).
- **Decision**: Extract `spectral_centroid` (`librosa.feature.spectral_centroid`), `rms` (`librosa.feature.rms`), `spectral_bandwidth` (`librosa.feature.spectral_bandwidth`), `spectral_contrast` (`librosa.feature.spectral_contrast`), `spectral_flatness` (`librosa.feature.spectral_flatness`), `spectral_rolloff` (`librosa.feature.spectral_rolloff`), `zero_crossing_rate` (`librosa.feature.zero_crossing_rate`), and `mfcc` (`librosa.feature.mfcc`) using `librosa`, array operations in `numpy`, and signal filtering in `scipy`.
- **Downsampling & Temporal Strategy**: For V1, collapse each feature's temporal frame vector into a single scalar summary value (downsampling the feature space to manageable scalar dimensions). Future program editions may retain temporal frame sequences (less downsampling) for time-series analysis.
- **Rationale**: `librosa` is the standard Python audio analysis library built on `numpy` and `scipy`, supporting MP3, WAV, and FLAC decoding via `soundfile` / `audioread` (`librosa` dependencies).
- **Alternatives Considered**: `pyAudioAnalysis` (less active maintenance), raw `scipy.io.wavfile` (lacks MP3/FLAC out-of-the-box support).

### 3. Database Interfacing & Storage (SQLAlchemy + PostgreSQL)

- **Decision**: Use SQLAlchemy ORM with PostgreSQL database engine via `psycopg` / `psycopg2`. Store song metadata in `songs` table and feature vectors in `song_fingerprints` table (storing feature vectors as JSONB / ARRAY of floats).
- **Rationale**: SQLAlchemy provides framework-agnostic ORM models compliant with Constitution Principle I (Standalone Library-First Architecture).
- **Alternatives Considered**: Raw SQL (harder to maintain), Django ORM for core logic (violates decoupling core library from Django web framework).

### 4. Django Frontend & 2-Click Match Selection UX

- **Decision**: Django view renders single page with search text field and search button. JavaScript handles AJAX calls to internal Django endpoints (`/search/` and `/confirm/`). Candidate matches render in a list. Click 1 highlights match ("Selected"), Click 2 on selected item triggers confirmation and initiates audio fetch + fingerprint generation.
- **Rationale**: Meets exact user requirement: text field, search button, candidate list with 2-click selection/confirmation flow.
- **Alternatives Considered**: Native HTML form submit (requires page refresh and loses smooth 2-click selection state).

### 5. Quality, Security & Testing Tooling (Pre-commit & CI)

- **Decision**: Integrate pre-commit hooks and dev tools into `pyproject.toml` / `.pre-commit-config.yaml`:
  - **Bandit**: Automated static analysis for security vulnerability detection.
  - **Radon**: Code metric analysis (cyclomatic complexity and maintainability index).
  - **FactoryBoy (`factory_boy`)**: Test fixture generation for integration test suites alongside `pytest`.
  - **Coverage (`pytest-cov`)**: Code coverage tracking and assertion.
- **Rationale**: Enforces strict code quality, security standards, and high test coverage across core DSP modules and integration layers.

### 6. Configuration Management (Hydra)

- **Decision**: Use Hydra (`hydra-core`) for all non-secret application configuration, stored in hierarchical YAML under `config/` with `defaults` groups (`logging`, `db`). Detailed design: [config-report.md](../../docs/001-song-fingerprint-engine/config-report.md).
- **Rationale**: Centralizes settings (levels, connection strings, retry counts, sample rates) outside logic, enables environment switching (dev/prod) via a single defaults/CLI switch, allows any key to be overridden on the command line without code edits, resolves secrets via `${env:...}` interpolation so credentials never enter the repo, and provides `--multirun` for future experimentation.
- **Alternatives Considered**: Raw `os.environ` reads (no structure, no defaults composition, no CLI overrides), bare OmegaConf YAML without Hydra (no `defaults`/override machinery), hard-coded defaults behind `argparse`/dataclasses (scattered, no env groups).
- **Constraint**: The project runs Python 3.14 but `hydra-core>=1.3.4` supports up to Python 3.11; plan the 1.4 development release pin accordingly (task T002).
