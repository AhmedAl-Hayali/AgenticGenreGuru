# API Flow: Song Fingerprint Engine

**Purpose**: Trace the expected happy path from user input through the internal API, the Deezer interface, the local database, and data return; then catalog the fault points where expected flow breaks and errors surface.
**Created**: 2026-08-05
**Feature**: `001-song-fingerprint-engine`
**Contracts**: [search-api.md](../../specs/001-song-fingerprint-engine/contracts/search-api.md), [deezer-api.md](../../specs/001-song-fingerprint-engine/contracts/deezer-api.md)
**Specs**: [spec.md](../../specs/001-song-fingerprint-engine/spec.md), [plan.md](../../specs/001-song-fingerprint-engine/plan.md), [data-model.md](../../specs/001-song-fingerprint-engine/data-model.md)

---

## 1. Actors & Components

| Component                             | Role                                                                                  |
|---------------------------------------|---------------------------------------------------------------------------------------|
| **User**                              | Submits a song title, confirms a match via the web UI                                 |
| **Django Frontend**                   | Serves UI; hosts internal `/api/search/` and `/api/confirm/` endpoints                |
| **backend core (`src/core/deezer/`)** | Calls Deezer `/search`; fetches the 30s preview MP3                                   |
| **backend core (`src/core/audio/`)**  | Runs librosa DSP feature extraction on the preview                                    |
| **backend core (`src/core/db/`)**     | SQLAlchemy repositories; dedup lookup by ISRC; persists `songs` + `song_fingerprints` |
| **Deezer API**                        | External catalog + preview source (`api.deezer.com/search`)                           |
| **PostgreSQL**                        | Local relational store (`songs`, `song_fingerprints`)                                 |

---

## 2. Happy Path (Success Flow)

```mermaid
flowchart TD
    U["User types song title"] --> A["GET /api/search/?query=..."]
    A --> D["Deezer /search?q=...&limit=5"]
    D --> A2["Return top 5 matches (id, title, isrc, duration, preview, artist, album)"]
    A2 --> UI["UI lists top 5 candidates"]
    UI --> C["User Click 1: select candidate"]
    C --> C2["Click 2: confirm selection"]
    C2 --> POST["POST /api/confirm/ {deezer_id, title, isrc, duration, preview, artist, album}"]
    POST --> LOC["Local DB lookup by isrc"]
    LOC -->|"no match"| FETCH["Fetch preview MP3 from Deezer"]
    FETCH --> DSP["DSP feature extraction (8 collapsed features)"]
    DSP --> DB["Store song metadata + feature vector"]
    DB --> RETURN["Return deezer_id + isrc + fingerprint to UI"]
```

### Step-by-step expectation

1. **User input** → `GET /api/search/?query={song_title}` (Django internal endpoint).
2. **Backend → Deezer** → `GET api.deezer.com/search?q={song_title}&limit=5` returns a Track array. GenreGuru keeps only `id`, `title`, `isrc`, `duration`, `preview`, `artist {id, name}`, `album {id, title}` (see the Track Object Field Reference in [deezer-api.md](../../specs/001-song-fingerprint-engine/contracts/deezer-api.md)).
3. **Search response returns top 5** → UI renders candidates and waits for the user.
4. **2-click confirmation** → `POST /api/confirm/` with `{deezer_id, title, isrc, duration, preview, artist, album}`.
5. **Local ISRC lookup** → `core/db/` queries `songs` by `isrc`.
6. **No local match**  → fetch the 30s preview MP3 from `preview` via `core/deezer/` (3 retries, 5s delay).
7. **DSP extraction** → `core/audio/` computes 8 features (`spectral_centroid`, `rms`, `spectral_bandwidth`, `spectral_contrast`, `spectral_flatness`, `spectral_rolloff`, `zero_crossing_rate`, `mfcc`), mono downmix, arithmetic-mean collapse to one scalar per feature.
8. **Persist** → writes `songs` (row: `id`, `deezer_id`, `isrc`, `title`, `artist`, `album`, `preview_url`, `duration`, `created_at`) and `song_fingerprints` (row: `id`, FK `song_id`, 8 feature columns, `audio_format`, `sample_rate`, `created_at`) — see [data-model.md](../../specs/001-song-fingerprint-engine/data-model.md).
9. **Return** → UI displays success + fingerprint metrics with `deezer_id`, `isrc`, and `status` (confirm response shape in [search-api.md](../../specs/001-song-fingerprint-engine/contracts/search-api.md)).

> **Already-stored track (reuse path)**: Local ISRC lookup finds a match → returns the stored fingerprint without generating a new feature vector (dedup per spec FR-006).

### API Abstract
- The flow is **read-retrieve-write-read**: internal `/api/search` → Deezer, UI confirmation → `/api/confirm` → local lookup / fetch / extract / write → response.
- No record is created unless the user confirms a match and an `isrc` is present (inconsistent records are never persisted). The only exception is the reuse path, which returns an earlier record before any fetch/extract.

---

## 3. Fault Points & Exceptions (Non-Happy Paths)

These interrupt the happy path and must surface an expected error instead of proceeding.

### 3.1 Network failures

| Fault                        | Origin                 | Expected behavior                                                                                                |
|------------------------------|------------------------|------------------------------------------------------------------------------------------------------------------|
| Deezer `/search` unreachable | Deezer / DNS / network | search cannot return matches; surface `"network disconnected"` (503)                                             |
| Preview MP3 fetch failure    | Deezer / network       | 3 retries at 5s interval → on all fail raise `NetworkDisconnectedError`; UI shows `"network disconnected"` (503) |

### 3.2 ISRC & record identity

| Fault                                        | Location                     | Expected Behavior                                                                                                                                                |
|----------------------------------------------|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| External Deezer response omits `isrc`        | Deezer interface (retrieval) | **Fail loud** — throw an error; do not persist without ISRC ([deezer-api.md](../../specs/001-song-fingerprint-engine/contracts/deezer-api.md) note, spec FR-005) |
| Search returns zero matches                  | `/api/search` → Deezer       | raise `TrackNotFoundError` (404) and show user `"No results found.\nMake sure everything is spelled correctly, or try searching for something different."`; no incomplete DB record created (spec scenario 2) |
| `isrc` already exists in `songs`             | DB lookup                    | local record found → reuse stored fingerprint, no duplicate rows (spec FR-006)                                                                                   |
| Concurrent duplicate submission, same `isrc` | DB write                     | DB unique constraint on `isrc` flips the second write into a uniqueness error rather than a duplicate record                                                     |

### 3.3 Audio / DSP processing

| Fault                                              | Expected Behavior                                                                                 |
|----------------------------------------------------|---------------------------------------------------------------------------------------------------|
| Fetched MP3/WAV/FLAC corrupted or unprocessable    | show `"audio file cannot be processed"` (400) (FR-008)                                            |
| Multi-channel audio                                | downmixed to mono before DSP; no error                                                            |
| Silent / non-musical file                          | valid zero/low-energy vector; no failure (edge case)                                              |
| `preview` empty string (unavailable/region-locked) | treat as fetch failure; surface `"network disconnected"` or fetch error so no success is produced |

### 3.4 Database / API-side errors

| Fault                                                                    | Expected Behavior                                                                                                                                      |
|--------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| DB write fails mid-persist (e.g., constraint violation, connection loss) | no partial/inconsistent record; return error; nothing returned to UI as success                                                                        |
| `POST /api/confirm/` with missing `isrc` in body                         | ISRC is mandatory → reject request and fail loud ([search-api.md](../../specs/001-song-fingerprint-engine/contracts/search-api.md) dedup note, FR-006) |
| Internal error anywhere in the pipeline                                  | transport as `status: "error"` with a message; do not fabricate a feature vector                                                                       |

---

## 4. Expected API Interactions (Sequence)

```mermaid
sequenceDiagram
    participant User
    participant UI as Django App
    participant Core as Backend core
    participant DZ as Deezer API
    participant DB as PostgreSQL
    User->>UI: song title
    UI->>Core: GET /api/search?query=...
    Core->>DZ: GET /search?q=...&limit=5
    DZ-->>Core: track[] {id, title, isrc, duration, preview, link, artist, album}
    Core-->>UI: top-5 matches
    UI-->>User: render candidates
    User->>UI: 2-click confirm
    UI->>Core: POST /api/confirm {deezer_id, isrc, title, artist, preview_url}
    Core->>DB: lookup songs by isrc
    alt isrc match
        DB-->>Core: stored song + fingerprint
        Core->>Core: reuse looked-up song + fingerprint
    else no isrc match
        DB-->>Core: no record
        Core->>DZ: GET preview MP3 (3 retries, 5s)
        DZ-->>Core: preview MP3 bytes
        Core->>Core: DSP extract 8 features
        Core->>DB: INSERT songs + song_fingerprints (isrc + deezer_id)
    end
    Core-->>UI: {status, song_id, fingerprint}
    UI-->>User: display result
```

### Key contract touchpoints
| Step    | Internal route       | External call                                       | Outcome on happy path              |
|---------|----------------------|-----------------------------------------------------|------------------------------------|
| Search  | `GET /api/search/`   | Deezer `/search`                                    | top-5 matches serialized           |
| Confirm | `POST /api/confirm/` | Deezer preview fetch (only when not already stored) | `deezer_id` + `isrc` + fingerprint |

---

## 5. Where single fallback to the "reuse" path short-circuits computing

- If the incoming `isrc` already exists locally → **no** Deezer preview fetch, no DSP run, no new row; the stored fingerprint is returned immediately.
- This is the primary optimized branch and the only one that skips `core/audio`.

---

## 6. Reference Checklist (adherence)

- ISRC is mandatory and read from the Deezer response; missing → fail loud, neither fallback nor silent. `FR-005`, `FR-006`
- Local miss is NOT an error → generates a new vector after fetching preview and running DSP. `FR-006`
- DSP: 8 collapsed features, mono downmix, arithmetic-mean collapse. `FR-003`
- MP3/WAV/FLAC only. `FR-002`
- 3 retries / 5s on fetch failure. `FR-007`, `NFR/Deezer §2`.

**Note to future readers**: maintain the [search-api.md](../../specs/001-song-fingerprint-engine/contracts/search-api.md) + [deezer-api.md](../../specs/001-song-fingerprint-engine/contracts/deezer-api.md) field references as the single source of truth for payload shapes; whenever Deezer changes its schema, those files change first, then re-read this flow diagram.