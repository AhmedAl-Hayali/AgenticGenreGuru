# Tasks: Song Fingerprint Engine

**Input**: Design documents from `/specs/001-song-fingerprint-engine/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests ARE REQUIRED. spec.md marks "User Scenarios & Testing *(mandatory)*" and the project Constitution mandates strict TDD (Red-Green-Refactor). Test tasks MUST be written first, confirmed failing, before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **\[P\]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions (from plan.md)

- **core library**: `src/core/audio/`, `src/core/deezer/`, `src/core/db/` at repository root
- **web app**: `frontend/fingerprint_app/`, `frontend/genreguru_web/`
- **tests**: `tests/unit/`, `tests/integration/`, `tests/contract/`
- **Stack**: Python 3.14, Django, SQLAlchemy + psycopg, librosa/numpy/scipy, httpx, PostgreSQL
- **Dev tooling**: pytest, pytest-django, pytest-mock, factory_boy, coverage, bandit, radon, ruff, ty

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create directory structure per plan.md: `src/core/audio/`, `src/core/deezer/`, `src/core/db/`, `frontend/genreguru_web/`, `frontend/fingerprint_app/`, `tests/unit/`, `tests/integration/`, `tests/contract/` (with `__init__.py` files), and the Hydra config tree `config/logging/` + `config/db/` (Hydra config groups)
- [ ] T002 Add runtime + dev dependencies to `pyproject.toml` (Django, SQLAlchemy, psycopg[binary], httpx, rich, pytest-django, pytest-mock, factory_boy, coverage, pytest-cov, bandit, radon); verify `hydra-core` pin works on Python 3.14 (upgrade to 1.4 dev release if needed per `docs/001-song-fingerprint-engine/config-report.md`)
- [ ] T003 \[P\] Scaffold Django project skeleton in `frontend/` (`manage.py`, `frontend/genreguru_web/__init__.py`, `settings.py`, `urls.py`, `asgi.py`, `wsgi.py` with `fingerprint_app` registered)
- [ ] T004 Configure pytest + pytest-django in `pyproject.toml` (`[tool.pytest.ini_options]` with `DJANGO_SETTINGS_MODULE=genreguru_web.settings` and `testpaths=tests`)
- [ ] T005 \[P\] Create Hydra config skeleton per `docs/001-song-fingerprint-engine/config-report.md`: `config/config.yaml` (`defaults: [logging: dev, db: dev, features: default, _self_]`), `config/logging/dev.yaml` + `config/logging/prod.yaml`, `config/db/dev.yaml` + `config/db/prod.yaml` (secrets only via `${env:...}` interpolation, never literal), `config/features/default.yaml` (`visualization.enabled: false`, `recommendations.enabled: false`) + `config/features/all.yaml`; add `src/core/config.py` compose helper (hydra.initialize + hydra.compose for the Django path); create `.env.example` documenting `DATABASE_URL` (default `postgresql://postgres:postgres@localhost:5432/genreguru`) and Django `SECRET_KEY`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement shared exception hierarchy in `src/core/errors.py` (`NetworkDisconnectedError`, `AudioProcessingError`, `TrackNotFoundError`, `MissingISRCError`, `PreviewUnavailableError`); each exception carries structured attrs (`isrc`, `deezer_id`, `code`, `attempts`) for structured log context; no logging inside exception classes
- [ ] T007 Implement database engine + session factory in `src/core/db/engine.py` (reads connection config from the Hydra `db` group via `src/core/config.py`, not hard-coded env parsing; creates SQLAlchemy `engine` + `SessionLocal` via psycopg); module logger: INFO on engine init (host/db/pool size, never the password), DEBUG session open/close, WARNING on pool/disconnect events
- [ ] T008 Create SQLAlchemy declarative `Base` in `src/core/db/base.py`
- [ ] T009 Create `Song` and `SongFingerprint` models in `src/core/db/models.py` per data-model.md (`songs`: uuid7 `id`, unique `deezer_id`, unique `isrc`, `title`, `artist`, `album`, `preview_url`, `duration`, `created_at`; `song_fingerprints`: uuid7 `id`, unique FK `song_id`, 8 collapsed float features, `audio_format`, `sample_rate`, `created_at`); keep models logging-free (persistence logging lives in the repository layer T024)
- [ ] T010 Implement table-creation script in `src/core/db/init_db.py` (runnable as `python -m src.core.db.init_db`); decorate with `@hydra.main(config_path="../../../config", config_name="config")` (or call the compose helper), then `setup_logging()`; INFO table-creation start/completion (count), `logger.exception` on failure
- [ ] T011 Configure logging infrastructure in `src/core/logging.py` per `docs/001-song-fingerprint-engine/logging-report.md` (loads the active Hydra `logging` config group per `docs/001-song-fingerprint-engine/config-report.md`, converts via `OmegaConf.to_container(resolve=True)`, feeds `logging.config.dictConfig` — no hard-coded dict; `JsonFormatter` + `NonErrorFilter` utils; stdout non-errors / stderr errors / rotating JSONL `logs/` handlers; named `QueueHandler` + `QueueListener`; package-root `NullHandler` for standalone-library safety; `setup_logging()` entrypoint; `LoggerAdapter` injecting `isrc`/`deezer_id`/`song_id`/`reused` context via `extra` for the reused=`true/false` fingerprint flag; dev-only `RichHandler` console pair — `rich_tracebacks=True`, `tracebacks_suppress=[django]`, `markup` off — driven by `logging.dev.rich` from YAML, never replacing the JSONL sink)
- [ ] T012 Create shared pytest fixtures in `tests/conftest.py` (test DB session, engine override, Django test client)
- [ ] T012a \[P\] Unit test for DB engine factory (`src/core/db/engine.py`): hydra `db` group ingestion, psycopg URL construction, engine type; assert failures on missing `${env:DATABASE_URL}` in prod group — in `tests/unit/test_engine.py`
- [ ] T012b \[P\] Integration test for `init_db` table creation (`python -m src.core.db.init_db`): all tables created idempotently, rerun-safe; assert schema matches data-model.md — in `tests/integration/test_init_db.py`
- [ ] T013 Create FactoryBoy factories `SongFactory` + `SongFingerprintFactory` in `tests/factories.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Song Input to Stored Audio Fingerprint (Priority: P1) 🎯 MVP

**Goal**: User inputs a song title, selects from the top 5 matches via 2-click confirm, system fetches the online audio snippet first, runs a composite DSP feature pipeline (8 collapsed features), and stores the fingerprint with `isrc` + `deezer_id` in PostgreSQL with ISRC-based dedup.

**Independent Test**: Submit a valid song title, confirm one of the top 5 matches, verify snippet is fetched before extraction, validate 8 collapsed features (`spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, `mfcc`), and check the vector is persisted with `isrc` + `deezer_id`. Re-submitting the same song reuses the stored fingerprint (ISRC match, no duplicate).

### Tests for User Story 1 (REQUIRED - write FIRST, confirm FAIL, then implement) ⚠️

- [ ] T014 \[P\] \[US1\] Unit tests for mono downmix loader + 8-feature extraction with arithmetic-mean collapse in `tests/unit/test_audio_features.py`
- [ ] T015 \[P\] \[US1\] Unit tests for Deezer search client (field mapping, missing `isrc` → `MissingISRCError`, empty `preview` → `PreviewUnavailableError`) in `tests/unit/test_deezer_client.py`
- [ ] T016 \[P\] \[US1\] Integration test for snippet-fetch retry (3 attempts, 5s delay, `NetworkDisconnectedError`) in `tests/integration/test_deezer_retry.py`
- [ ] T017 \[P\] \[US1\] Integration test for `SongRepository` dedup-by-ISRC persistence (fresh insert vs reuse) in `tests/integration/test_repositories.py`
- [ ] T018 \[P\] \[US1\] Contract test for `GET /api/search/` (top-5, 404 `TrackNotFoundError`, 503 `NetworkDisconnectedError`) in `tests/contract/test_search_api.py`
- [ ] T019 \[P\] \[US1\] Contract test for `POST /api/confirm/{match}` (fresh fingerprint, ISRC-reuse path, 400 `AudioProcessingError`, 503 `NetworkDisconnectedError`) in `tests/contract/test_confirm_api.py`

### Implementation for User Story 1

- [ ] T020 \[P\] \[US1\] Implement audio snippet loader with mono downmix (mean of channels) in `src/core/audio/loader.py`; module logger: DEBUG source/sample_rate/channels/duration/format + mono-downmix, ERROR `logger.exception` → `AudioProcessingError` (REQ-015 message), lazy `%s` args, never log binary buffer
- [ ] T021 \[P\] \[US1\] Implement feature extractor computing `spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, `mfcc` (librosa/numpy/scipy) with arithmetic-mean collapse to scalars in `src/core/audio/features.py`; module logger: DEBUG frame shape + per-feature collapse mean, WARNING/INFO on zero/low-energy frames (silent-non-musical edge case), INFO extraction complete + elapsed (SC-002)
- [ ] T022 \[P\] \[US1\] Implement Deezer search client in `src/core/deezer/client.py` (`GET https://api.deezer.com/search?q={query}&limit=5`, Track field mapping, fail-loud on missing `isrc`/`preview`, error-code mapping per `contracts/deezer-api.md`); module logger: INFO request query+limit=5 and response `total`, DEBUG counts only (no payload dumps), WARNING on `QUOTA`(4)/`SERVICE_BUSY`(700) before retry, ERROR `logger.exception` on missing `isrc` → `MissingISRCError` and empty `preview` → `PreviewUnavailableError` with `extra={isrc, deezer_id}`
- [ ] T023 \[P\] \[US1\] Implement audio snippet fetcher with 3x retry / 5s delay (`NetworkDisconnectedError` on all-fail) in `src/core/deezer/snippets.py`; module logger: INFO fetch start/success (bytes, elapsed), WARNING per retry (`attempt=%d delay=%ds`), ERROR+`logger.exception` → `NetworkDisconnectedError` after 3rd fail (REQ-013/014), never log bytes
- [ ] T024 \[P\] \[US1\] Implement `SongRepository` with `find_by_isrc()` + `create_song_and_fingerprint()` in `src/core/db/repositories.py`; module logger: INFO `isrc` lookup hit/miss, INFO insert (`song_id`/`isrc`/`deezer_id`), WARNING on concurrent same-`isrc` unique violation (api_flow §3.2)
- [ ] T025 \[US1\] Implement `FingerprintService` orchestration in `src/core/fingerprint_service.py` (ISRC reuse path short-circuits; else fetch → extract → store; logs `reused=true/false` via the T011 `LoggerAdapter` — `extra={isrc, deezer_id, song_id, reused}`; INFO `"fingerprint reused (isrc=...)"` vs `"fresh fingerprint generated (isrc=..., elapsed=...s)"`; `logger.exception` on catch before re-raise)
- [ ] T026 \[US1\] Implement search view `GET /api/search/` in `frontend/fingerprint_app/views.py` (404 `TrackNotFoundError`, 503 `NetworkDisconnectedError` per `contracts/search-api.md`)
- [ ] T027 \[US1\] Implement confirm view `POST /api/confirm/{match}` in `frontend/fingerprint_app/views.py` (400 `AudioProcessingError`, 503 `NetworkDisconnectedError`, response payload incl. `song_id`, `deezer_id`, `isrc`, `fingerprint` with `vector_length: 8`)
- [ ] T028 \[US1\] Register `/api/search/` and `/api/confirm/` routes in `frontend/fingerprint_app/urls.py` and include them in `frontend/genreguru_web/urls.py`
- [ ] T029 \[US1\] Create `index.html` template (search bar, top-5 candidate list, result area) in `frontend/fingerprint_app/templates/fingerprint_app/index.html`
- [ ] T030 \[US1\] Implement 2-click selection/confirmation JS (Click 1 highlight "Selected", Click 2 confirm + POST) in `frontend/fingerprint_app/static/fingerprint_app/app.js`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Fingerprint Feature Retrieval & Inspection (Priority: P2)

**Goal**: Users list stored catalog entries and inspect the full set of stored fingerprint feature fields for any previously processed song.

**Independent Test**: Query stored songs from the database and read out the complete extracted fingerprint feature set per song; list all available songs with metadata summary.

### Tests for User Story 2 (REQUIRED - write FIRST, confirm FAIL, then implement) ⚠️

- [ ] T031 \[P\] \[US2\] Integration test for repository `list_songs()` + `get_fingerprint_by_isrc()` in `tests/integration/test_repository_queries.py`
- [ ] T032 \[P\] \[US2\] Contract test for `GET /api/songs/` (catalog summary) and `GET /api/songs/{isrc}/` (full fingerprint detail) in `tests/contract/test_songs_api.py`

### Implementation for User Story 2

- [ ] T033 \[P\] \[US2\] Add `list_songs()` + `get_fingerprint_by_isrc()` methods in `src/core/db/repositories.py`
- [ ] T034 \[US2\] Implement catalog list view `GET /api/songs/` in `frontend/fingerprint_app/views.py` (summary of songs + fingerprint metadata)
- [ ] T035 \[US2\] Implement song detail view `GET /api/songs/{isrc}/` in `frontend/fingerprint_app/views.py` (structured full fingerprint + song metadata)
- [ ] T036 \[US2\] Add catalog listing + song detail render sections in `frontend/fingerprint_app/templates/fingerprint_app/index.html`
- [ ] T037 \[US2\] Register `/api/songs/` and `/api/songs/{isrc}/` routes in `frontend/fingerprint_app/urls.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Digital Signal Processing Visualization (Priority: P3)

**Goal**: Users view a spectrogram of a fingerprinted song with the spectral centroid highlighted and top contributing feature factors, on demand.

**Independent Test**: Select a processed song and toggle visualization mode to verify spectrogram rendering and feature-factor highlighting.

### Tests for User Story 3 (REQUIRED - write FIRST, confirm FAIL, then implement) ⚠️

- [ ] T038 \[P\] \[US3\] Unit tests for visualization data builder (spectrogram + centroid overlay + factor contributions) in `tests/unit/test_visualization.py`

### Implementation for User Story 3

- [ ] T039 \[P\] \[US3\] Implement spectrogram/visualization data generation (spectrogram, spectral-centroid overlay, top feature contribution factors via librosa matplotlib/numpy) in `src/core/audio/visualization.py`; module logger: INFO generation complete (`song_id`), DEBUG spectrogram params (never log the spectrogram matrix)
- [ ] T040 \[US3\] Implement `GET /api/songs/{isrc}/visualization/` endpoint in `frontend/fingerprint_app/views.py`
- [ ] T041 \[US3\] Add visualization toggle + spectrogram render in `frontend/fingerprint_app/templates/fingerprint_app/index.html` and `frontend/fingerprint_app/static/fingerprint_app/app.js`
- [ ] T042 \[US3\] Register visualization route in `frontend/fingerprint_app/urls.py`

**Checkpoint**: User Story 3 functional and testable independently

---

## Phase 5b: User Story 4 - Custom Feature Vector Modification for Recommendations (Priority: P3)

**Goal**: Users adjust acoustic feature sliders on a processed song so recommendations are generated against the modified vector rather than the original track.

**Independent Test**: Adjust feature vector values on a song profile and verify the recommendation query results change accordingly.

### Tests for User Story 4 (REQUIRED - write FIRST, confirm FAIL, then implement) ⚠️

- [ ] T043 \[P\] \[US4\] Integration test for modified-vector recommendation query (top-N matches change with adjusted vector) in `tests/integration/test_recommendations.py`

### Implementation for User Story 4

- [ ] T044 \[P\] \[US4\] Implement `RecommendationService` (cosine similarity over the 8-dimensional fingerprint vectors) in `src/core/recommendations.py`; module logger: INFO result size + top-N similarity scores, WARNING on fewer candidates than N or degenerate (all-zero) query vector
- [ ] T045 \[US4\] Implement `POST /api/recommend/` endpoint (accepts modified vector, returns top matches) in `frontend/fingerprint_app/views.py`
- [ ] T046 \[US4\] Add acoustic feature slider controls + recommendation list render in `frontend/fingerprint_app/templates/fingerprint_app/index.html` and `frontend/fingerprint_app/static/fingerprint_app/app.js`
- [ ] T047 \[US4\] Register `/api/recommend/` route in `frontend/fingerprint_app/urls.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T048 \[P\] Create `.pre-commit-config.yaml` (ruff, bandit, ty) and run it on the full tree
- [ ] T049 \[P\] Run bandit security audit over `src/` and `frontend/`; fix findings
- [ ] T050 \[P\] Run radon complexity analysis on `src/core/`; refactor any module exceeding cyclomatic complexity 10
- [ ] T051 \[P\] Run coverage report over `tests/`; add missing tests to satisfy Constitution III coverage expectations
- [ ] T052 \[P\] Benchmark performance: confirm SC-002 (<10s extraction per snippet) and SC-005 (<500ms ISRC reuse lookup) in `tests/benchmarks/`
- [ ] T053 \[P\] Validate quickstart.md Scenario 1 end-to-end (search → 2-click confirm → fingerprint → dedup reuse) and run `pytest tests/`
- [ ] T054 \[P\] Update `docs/001-song-fingerprint-engine/` with implementation notes and any contract deviations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Backend/core user story work can proceed in parallel (if staffed) — but UI frontend tasks are serialized (they share `index.html`/`app.js`)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Reads US1's `Song`/`SongFingerprint` tables but is independently testable (list + query existing data)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses US1 audio/DB layers but independently testable via stored songs
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Uses US1 persisted vectors but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD / Constitution III)
- Models before services (Foundation)
- Services before endpoints
- Core implementation before integration (Django views)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked \[P\] can run in parallel (T003-T005 are separate files)
- All Foundational tasks marked **without** \[P\] are sequential (T009 models, T010 init_db depend on engine/base); T012 and T013 can overlap once models exist
- Once Foundational completes, all user stories can start in parallel (team capacity permitting)
- All tests within a story marked \[P\] run in parallel (separate test files)
- US1 core-library tasks T020-T024 run in parallel (separate modules)
- Different user stories parallelizable across team members

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (write first, confirm failing):
Task: "Unit tests for mono downmix + feature extraction in tests/unit/test_audio_features.py"
Task: "Unit tests for Deezer search client in tests/unit/test_deezer_client.py"
Task: "Integration test for snippet retry in tests/integration/test_deezer_retry.py"
Task: "Integration test for repository dedup in tests/integration/test_repositories.py"
Task: "Contract test for GET /api/search/ in tests/contract/test_search_api.py"
Task: "Contract test for POST /api/confirm/ in tests/contract/test_confirm_api.py"

# Launch all core-library implementations together:
Task: "Implement audio loader mono downmix in src/core/audio/loader.py"
Task: "Implement 8-feature extractor in src/core/audio/features.py"
Task: "Implement Deezer search client in src/core/deezer/client.py"
Task: "Implement snippet fetcher with retry in src/core/deezer/snippets.py"
Task: "Implement SongRepository in src/core/db/repositories.py"
```

## Parallel Example: User Story 2

```bash
# Launch US2 tasks together (tests first, then implementation):
Task: "Integration tests for repository queries in tests/integration/test_repository_queries.py"
Task: "Contract tests for songs API in tests/contract/test_songs_api.py"
Task: "Add list_songs + get_by_isrc in src/core/db/repositories.py"
```

## Parallel Example: User Story 3

```bash
Task: "Unit tests for visualization builder in tests/unit/test_visualization.py"
Task: "Implement visualization data generation in src/core/audio/visualization.py"
```

## Parallel Example: User Story 4

```bash
Task: "Integration test for recommendations in tests/integration/test_recommendations.py"
Task: "Implement RecommendationService in src/core/recommendations.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (`pytest tests/unit/ tests/integration/ tests/contract/`)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 (P3) → Test independently → Deploy/Demo
5. Add User Story 4 (P3) → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done, backend/core work is parallel-safe across stories (all core-library and endpoint tasks live in separate modules):
   - Developer A: User Story 1 (core + endpoints + UI for search/confirm)
   - Developer B: User Story 2 (core + endpoints)
   - Developer C: User Story 3 / 4 (core + endpoints)
3. UI integration is the serial bottleneck: US1/2/3/4 frontend tasks all edit the SAME files (`frontend/fingerprint_app/templates/fingerprint_app/index.html` + `.../static/fingerprint_app/app.js`). These tasks (T029/T030, T036, T041, T046) MUST be done sequentially ON ONE workstream to avoid merge conflicts — they can NOT run in parallel.
4. Core/endpoint tasks per story run in parallel; UI tasks are consolidated and merged into `index.html`/`app.js` one story at a time.

---

## Notes

- \[P\] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (Constitution III TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- UI tasks share `index.html`/`app.js` — mark them non-parallel and serialize across stories
- Performance targets: SC-001 95% query success, SC-002 <10s/snippet, SC-003 100% persistence, SC-005 <500ms reuse lookup