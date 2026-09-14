# GenreGuru Documentation

Index of all documentation in this repo. Folders render their `README.md`
as directory landing pages on GitHub; this is the entry point for `docs/`.

## Top-level documents

| File                                                   | Purpose                                                                                                                 |
|--------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md)                   | Project architecture — context/container, components, runtime flow, API surface, cross-cutting concerns, evolution path |
| [`API.md`](API.md)                                     | API guide: pdoc reference, internal/external contracts, endpoint table                                                  |
| [`adr/index.md`](adr/index.md)                         | Architecture Decision Records (ADR log)                                                                                 |
| [`ROADMAP.md`](ROADMAP.md)                             | Idea backlog + roadmap (completed / in progress / planned)                                                              |
| [`QUICKSTART.md`](../QUICKSTART.md)                    | End-user quickstart — setup, run, validation (repo root)                                                                |
| [`constitution.md`](constitution.md)                   | Project constitution — core principles, engineering standards, governance                                               |
| [`docstring-style-guide.md`](docstring-style-guide.md) | Google-style docstring conventions (enforced by Ruff `D` rules, rendered by pdoc)                                       |

## Feature design reports — `001-song-fingerprint-engine/`

| File                                                                                             | Purpose                                                   |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| [`001-song-fingerprint-engine/requirements.md`](001-song-fingerprint-engine/requirements.md)     | EARS requirement statements (REQ-001..019), authoritative |
| [`001-song-fingerprint-engine/api_flow.md`](001-song-fingerprint-engine/api_flow.md)             | Happy path, fault points, sequence diagrams               |
| [`001-song-fingerprint-engine/config-report.md`](001-song-fingerprint-engine/config-report.md)   | Hydra config tree design + conventions                    |
| [`001-song-fingerprint-engine/logging-report.md`](001-song-fingerprint-engine/logging-report.md) | Logging design, per-module rules                          |
| [`001-song-fingerprint-engine/lint-report.md`](001-song-fingerprint-engine/lint-report.md)       | Lint/toolchain report                                     |

## Generated reference (pdoc)

- `pdoc/` — generated HTML API reference (**gitignored** build artifact).
  Build: `uv run pdoc -o docs/pdoc/ -d google --mermaid -t docs/pdoc_templates genreguru genreguru_web fingerprint_app`. Live deploy: GitHub Pages via `.github/workflows/docs.yml`.
- `pdoc_templates/` — pdoc template overrides (`index.html.jinja2`, `module.html.jinja2`).

## Entry points

- **For contributors**: [README.md](../README.md) (root) → `docs/` index → [`ARCHITECTURE.md`](ARCHITECTURE.md) → feature specs ([specs/README.md](../specs/README.md)).
- **For API consumers**: [`API.md`](API.md) → pdoc + contracts.
- **For decision history**: [`adr/index.md`](adr/index.md).
- **For what is being worked on / next**: [`ROADMAP.md`](ROADMAP.md).