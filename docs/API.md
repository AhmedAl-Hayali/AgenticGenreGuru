# API Reference & Contracts

Top-level guide to GenreGuru's API surface. The authoritative generated
reference is **pdoc** output; this page ties the generated reference to the
contracted endpoint/payload documentation and the internal/external API
contracts.

## Generated reference (pdoc)

- **Local build**: `docs/pdoc/index.html` (gitignored build output; run
  `uv run pdoc -o docs/pdoc/ -d google --mermaid -t docs/pdoc_templates genreguru genreguru_web fingerprint_app` from the repo root).
- **Live**: [https://ahmedal-hayali.github.io/AgenticGenreGuru/](https://ahmedal-hayali.github.io/AgenticGenreGuru/)
  — built from `genreguru` docstrings by `.github/workflows/docs.yml` (deploys
  on `main` pushes touching `**.py`). Docstring conventions:
  [`docs/docstring-style-guide.md`](docstring-style-guide.md).

## Contract documents

| Contract                                                                                      | Scope                                                                 | Status      |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|-------------|
| [`contracts/search-api.md`](../specs/001-song-fingerprint-engine/contracts/search-api.md)     | Internal Django REST API (`/api/search/`, `/api/confirm/`)            | Implemented |
| [`contracts/deezer-api.md`](../specs/001-song-fingerprint-engine/contracts/deezer-api.md)     | External Deezer API (`/search`, `/track/{id}`, previews), error codes | Live        |
| [`contracts/traceability.md`](../specs/001-song-fingerprint-engine/contracts/traceability.md) | Contract-to-requirement mapping                                       | Tracking    |

## Endpoint table

From [`specs/…/contracts/search-api.md`](../specs/001-song-fingerprint-engine/contracts/search-api.md); `search` and `confirm` are implemented (Django routes).

| Method | Endpoint                           | Description                                                | Status      |
|--------|------------------------------------|------------------------------------------------------------|-------------|
| `GET`  | `/api/search/?query={title}`       | Search songs via Deezer, returns top 5 matches             | Implemented |
| `POST` | `/api/confirm/`                    | Confirm selection, generate or reuse fingerprint           | Implemented |
| `GET`  | `/api/songs/`                      | List all stored songs with fingerprint metadata            | Target      |
| `GET`  | `/api/songs/{isrc}/`               | Get full fingerprint detail for a song                     | Target      |
| `GET`  | `/api/songs/{isrc}/visualization/` | Spectrogram + top-3 factor viz (feature-gated)             | Optional    |
| `POST` | `/api/recommend/`                  | Cosine-similarity top-5 vs modified vector (feature-gated) | Optional    |

## Related
- [`docs/README.md`](README.md) — full documentation index.
- Flow/fault diagrams: [`docs/001-song-fingerprint-engine/api_flow.md`](001-song-fingerprint-engine/api_flow.md).