# Specifications

Index of feature specifications for GenreGuru. One feature is currently
specified: `001-song-fingerprint-engine`. Contents under each feature
directory and how the artifacts relate.

## 001-song-fingerprint-engine

### Documents

| File                                                                                                 | Purpose                                                                           |
|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [`001-song-fingerprint-engine/spec.md`](001-song-fingerprint-engine/spec.md)                         | Feature spec — user stories, requirements (REQ), scenarios, success criteria (SC) |
| [`001-song-fingerprint-engine/requirements.md`](../docs/001-song-fingerprint-engine/requirements.md) | EARS-converted requirements (authoritative, in `docs/`)                           |
| [`001-song-fingerprint-engine/plan.md`](001-song-fingerprint-engine/plan.md)                         | Implementation plan — processors, stack/dependency decisions, phases              |
| [`001-song-fingerprint-engine/data-model.md`](001-song-fingerprint-engine/data-model.md)             | `songs` / `song_artists` / `song_fingerprints` schema, ERD, design rules          |
| [`001-song-fingerprint-engine/research.md`](001-song-fingerprint-engine/research.md)                 | Technology selection rationale                                                    |
| [`QUICKSTART.md`](../QUICKSTART.md)                                                                  | Runtime entrypoints and validation paths (end-user guide, repo root)              |
| [`001-song-fingerprint-engine/tasks.md`](001-song-fingerprint-engine/tasks.md)                       | Task breakdown (T001+), checkpoints, execution status                             |

### Contracts

| File                                                                                                             | Scope                             |
|------------------------------------------------------------------------------------------------------------------|-----------------------------------|
| [`001-song-fingerprint-engine/contracts/search-api.md`](001-song-fingerprint-engine/contracts/search-api.md)     | Internal Django REST API          |
| [`001-song-fingerprint-engine/contracts/deezer-api.md`](001-song-fingerprint-engine/contracts/deezer-api.md)     | External Deezer API + error codes |
| [`001-song-fingerprint-engine/contracts/traceability.md`](001-song-fingerprint-engine/contracts/traceability.md) | Contract-to-requirement mapping   |

### Checklists

| File                                                                                                               | Scope                                 |
|--------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| [`001-song-fingerprint-engine/checklists/requirements.md`](001-song-fingerprint-engine/checklists/requirements.md) | Requirements implementation checklist |
| [`001-song-fingerprint-engine/checklists/api.md`](001-song-fingerprint-engine/checklists/api.md)                   | API implementation checklist          |

## Relationships

```text
spec.md ──► requirements.md (EARS, docs/) ──► contracts/*.md ──► traceability.md
   │
   ├──► plan.md ──► tasks.md (module map / status)
   ├──► data-model.md ──► docs/001-song-fingerprint-engine/api_flow.md
   └──► research.md / QUICKSTART.md (root) ──► docs/ARCHITECTURE.md (entry point)
```

- Design reports live in [`docs/001-song-fingerprint-engine/`](../docs/001-song-fingerprint-engine/); specs live here.
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) is the top-level architecture entry; [`docs/ROADMAP.md`](../docs/ROADMAP.md) tracks what is being worked on next.