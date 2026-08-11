# API Contract Traceability Matrix: Song Fingerprint Engine

**Purpose**: Verify every behavior defined in the API contracts ([deezer-api.md](deezer-api.md), [search-api.md](search-api.md)) traces back to a spec functional requirement, user-story acceptance scenario, or measurable success criterion; flag orphan behaviors. Satisfies checklist [CHK025](../checklists/api.md#traceability--dependencies).
**Created**: 2026-08-10
**Feature**: [spec.md](../spec.md)
**Contracts**: [deezer-api.md](deezer-api.md), [search-api.md](search-api.md)
Re-check after any contract or spec change: matrix must stay in sync with both directions.

## External Contract ([deezer-api.md](deezer-api.md))

| #    | Behavior                                                                                                                                                    | § | Spec anchor            | Status         |
|------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|---|------------------------|----------------|
| dz01 | `GET https://api.deezer.com/search?q={song_title}&limit=5` returns `data[]` + `total`                                                                       | 1 | **FR-001**             | Traced         |
| dz02 | Top-5 cap via `limit=5`                                                                                                                                     | 1 | **FR-001**             | Traced         |
| dz03 | Track field map (`id`, `title`, `isrc`, `duration`, `preview`, `artist`, `album`)                                                                           | 1 | **FR-005**             | Traced → Note  |
| dz04 | `isrc` absent → fail loud + user-facing message                                                                                                             | 1 | **FR-014**, **FR-015** | Traced         |
| dz05 | `preview` absent → fail loud + user-facing message                                                                                                          | 1 | **FR-016**             | Traced *(new)* |
| dz06 | HTTP GET on `preview` audio snippet (30s `.mp3`); retry 3× (5s cooldown between attempts) on network failure. All retries fail → `NetworkDisconnectedError` | 2 | **FR-002**, **FR-007** | Traced         |

## Internal Contract ([search-api.md](search-api.md))

| #    | Behavior                                                                                                                                       | § | Spec anchor                               | Status |
|------|------------------------------------------------------------------------------------------------------------------------------------------------|---|-------------------------------------------|--------|
| sa01 | `GET /api/search/?query={song_title}` returns top-5 matches                                                                                    | 1 | **FR-001**                                | Traced |
| sa02 | Zero search matches → `TrackNotFoundError` (404) + user-facing message                                                                         | 1 | **FR-001**                                | Traced |
| sa03 | Deezer `/search` unreachable; retry 3× (5s cooldown between attempts) on network failure. All retries fail → `NetworkDisconnectedError` (503)  | 1 | **FR-007**                                | Traced |
| sa04 | `POST /api/confirm/{match}` local `isrc` match → reuse stored fingerprint                                                                      | 2 | **FR-006**                                | Traced |
| sa05 | `POST /api/confirm/{match}` no local `isrc` match → fetch snippet, extract features, persist in local database                                 | 2 | **FR-002**, **FR-003**, **SC-003**        | Traced |
| sa06 | Snippet fetch network failure; retry 3× (5s cooldown between attempts) on network failure. All retries fail → `NetworkDisconnectedError` (503) | 2 | **FR-007**                                | Traced |
| sa07 | Unprocessable audio → `AudioProcessingError` (400)                                                                                             | 2 | **FR-008**                                | Traced |

## Reverse pass: FR → contract surface

- **FR-004** / **FR-005** surface in [search-api.md](search-api.md) §2 and are enforced in [data-model.md](../data-model.md).
- **FR-009** is enforced in [data-model.md](../data-model.md).
- <span style='color:red'>**FR-010** / **FR-011** are expectedly not present in contracts — future scope.</span>
- **FR-012** / **FR-013** surface in [search-api.md](search-api.md) §2 and are enforced in [data-model.md](../data-model.md).
- **SC-002** and **SC-003** are enforced by [search-api.md](search-api.md) §2 as described in §3.
- **SC-004** is enforced by both contracts, [deezer-api.md](deezer-api.md) & [search-api.md](search-api.md), together.
- <span style='color:red'>**SC-001** must be expanded on to capture how it's tested. Perhaps search by billboard hot 100 for the past X weeks?</span>
- <span style='color:red'>**SC-005** must be expanded on to capture how it's tested.</span>

## Notes
- **dz03** is missing the *processing timestamp* outlined in **FR-005**, but that is handled by the database core implementation, and is captured in [data-model.md](../data-model.md).
