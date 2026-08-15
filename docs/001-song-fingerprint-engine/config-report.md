# Configuration Management Report: Song Fingerprint Engine

**Purpose**: Authoritative design for configuration management in `src/core/` using Hydra. Derived from the Hydra docs (https://hydra.cc/docs/intro/) and the CodeCut article "Stop Hard-Coding in a Data Science Project: Use Configuration Files Instead" (https://codecut.ai/stop-hard-coding-in-a-data-science-project-use-configuration-files-instead/). This report is the single source of truth for how `config/` is structured, loaded, overridden, and secured. Logging-specific configuration details are documented in [logging-report.md](logging-report.md).
**Created**: 2026-08-13
**Feature**: `001-song-fingerprint-engine`
**Applicable tasks**: T001 (config tree), T005 (config skeleton + `src/core/config.py` + `.env.example`), T007 (db group), T010 (`@hydra.main`), T011 (logging group consumer)

---

## 1. Decision & Motivation

Hydra (`hydra-core`) manages all non-secret application configuration for this feature. Per the CodeCut article, hard-coding values (connection strings, file paths, levels, rotation sizes, retry counts, sample rates) across modules is brittle — updates get missed in one file, code cannot adapt to environments without edits, and secrets leak into source. Hydra solves this by:

- Storing settings in hierarchical YAML, separate from logic.
- Composing configs from `defaults` groups (environment switching is a one-line change).
- Allowing any value to be overridden from the command line at runtime.
- Resolving secrets from the environment via `${env:...}` interpolation so credentials never enter the repo.
- Supporting `--multirun` for sweeping parameter combinations (future experimentation).

### Alternatives considered

| Option                                       | Pros                                                                           | Cons                                                                                        | Decision |
|----------------------------------------------|--------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|----------|
| **Hydra (selected)**                         | Hierarchical YAML, defaults groups, CLI overrides, env interpolation, multirun | Slight learning curve; `@hydra.main` changes CWD/argv (compose API used for Django instead) | Chosen   |
| Raw `os.environ` everywhere                  | Zero deps, simple                                                              | No structure/typing, no defaults composition, hard to audit, no CLI overrides               | Rejected |
| Bare OmegaConf YAML (no Hydra)               | Hierarchical access                                                            | No `defaults` composition, no CLI override machinery, no multirun                           | Rejected |
| `argparse` / dataclasses hard-coded defaults | Typed                                                                          | Scattered across modules, no env groups, no override-of-any-key                             | Rejected |

---

## 2. Config Tree

```text
config/
├── config.yaml               # top-level entrypoint: defaults list + shared values
├── logging/                  # config group: logging setup (dev/prod)
│   ├── dev.yaml
│   └── prod.yaml
├── db/                       # config group: database connection (dev/prod)
│   ├── dev.yaml
│   └── prod.yaml
└── features/                 # config group: optional-feature flags (REQ-018/REQ-019 gating)
    ├── default.yaml          # visualization.enabled: false, recommendations.enabled: false
    └── all.yaml              # both enabled
```

Future groups (added as their tasks land): `audio/` (sample rate, frame parameters), `deezer/` (base URL, `limit=5`, retry count/delay), `retry/` (shared 3x/5s network policy), `recommend/` (top-N=5, distance metric).

### `config/config.yaml`

```yaml
defaults:
  - logging: dev        # switch to `logging=prod` at runtime
  - db: dev             # `db=prod` swaps connection without code changes
  - features: default   # REQ-018/REQ-019 optional features OFF by default
  - _self_
```

### Config groups (environment-specific values)

```text
config/logging/dev.yaml      # level: DEBUG, formatters/console + json, handlers, queue on, rich: true
config/logging/prod.yaml     # level: INFO/WARNING, JSONL-centric, tighter rotation, rich: false
config/db/dev.yaml           # url: postgresql://postgres:postgres@localhost:5432/genreguru
config/db/prod.yaml          # url: ${env:DATABASE_URL}  (secret stays out of YAML/repo)
config/features/default.yaml # visualization.enabled: false, recommendations.enabled: false (REQ-018/019 OFF)
config/features/all.yaml     # visualization.enabled: true, recommendations.enabled: true
```

---

## 3. Conventions

1. **Secrets via env interpolation, never committed.** Use OmegaConf `${env:VAR}` interpolation so credentials resolve at load time and are never written to YAML (matches the CodeCut security point and Constitution Rule "no secrets in source"). `.env.example` documents which variables are required (see T005).
2. **Dot-notation access.** Code reads `cfg.logging.level`, `cfg.db.url`, etc. Convert to a plain object when a stdlib consumer needs it: `OmegaConf.to_container(cfg, resolve=True)` (e.g. the `dictConfig` dict in `src/core/logging.py`).
3. **Override from the CLI, no code edits.** Examples:
   - `python -m src.core.db.init_db logging.level=DEBUG`
   - `python -m src.core.db.init_db db=prod`
   - `python -m src.core.db.init_db logging.handlers.file_all.maxBytes=20971520`
4. **Environment groups via `defaults`.** Following the CodeCut `database=dev/prod` pattern, `logging` and `db` are Hydra config groups so dev vs prod is a single defaults/CLI switch, with granular per-key override still available.
5. **`@hydra.main` for standalone scripts, compose API for Django.**
   - Standalone CLI (`python -m src.core.db.init_db`) uses `@hydra.main(config_path="../../../config", config_name="config", version_base=None)`.
   - The Django application MUST NOT use `@hydra.main` (it changes the working directory and hijacks `argv`). It uses the compose API — `hydra.initialize(version_base=None, config_path=...)` + `hydra.compose(config_name="config")` — wrapped in `src/core/config.py` and invoked once from Django `settings.py`.
6. **Security hygiene.** Never commit `*.yaml` containing raw credentials; secret-bearing values live behind `${env:...}` in a group file. `config/*.yaml` are plain project files (committed); secrets come from the environment only.

---

## 4. Per-Module Usage

| Consumer                 | Module / task                      | Config group             | Notes                                                                                                                         |
|--------------------------|------------------------------------|--------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Engine + session factory | `src/core/db/engine.py` (T007)     | `db`                     | Read `cfg.db.url`, pool params from group; log host/db (never password)                                                       |
| Logging setup            | `src/core/logging.py` (T011)       | `logging`                | Convert to dict via `OmegaConf.to_container(resolve=True)` → `logging.config.dictConfig`; Rich toggle from `logging.dev.rich` |
| Table creation CLI       | `src/core/db/init_db.py` (T010)    | `@hydra.main` → `config` | Entrypoint loads composed config, calls `setup_logging()`                                                                     |
| Config bootstrap helper  | `src/core/config.py` (T005)        | compose API              | `hydra.initialize` + `hydra.compose` for the Django path                                                                      |
| Future: DSP params       | `src/core/audio/*`                 | `audio`                  | sample rate, frame/hop sizes (default `22050` per data-model)                                                                 |
| Future: Deezer client    | `src/core/deezer/*`                | `deezer`, `retry`        | base URL, `limit=5`, 3x/5s retry policy                                                                                       |
| Future: recommendations  | `src/core/recommendations.py`      | `recommend`              | top-N=5, distance metric                                                                                                      |
| Optional-feature gating  | US3/US4 endpoints + UI (T040-T047) | `features`               | REQ-018/REQ-019 behavior only when `features.visualization.enabled` / `features.recommendations.enabled` = true               |

---

## 5. Security & Environment

- Required env vars are documented in `.env.example` (created by T005): `DATABASE_URL`, Django `SECRET_KEY`. Future: `DEEZER_API_KEY` (none needed for public V1 search).
- YAML values that reference the environment use `${env:VAR}`; missing variables fail fast at load time rather than silently.
- No logging/error message may echo the resolved secret value (see [logging-report.md](logging-report.md) Rule 10).

---

## 6. Traceability

| Design element                                            | Source                                                                                                                                                      |
|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Hydra config-driven application (no hard-coded constants) | Hydra docs (https://hydra.cc/docs/intro/); CodeCut article (https://codecut.ai/stop-hard-coding-in-a-data-science-project-use-configuration-files-instead/) |
| Env-interpolated secrets, out of repo                     | CodeCut article (Security section); Constitution Rule "no secrets in source"                                                                                |
| Default `sample_rate` 22050 (future `audio` group)        | [data-model.md](../../specs/001-song-fingerprint-engine/data-model.md)                                                                                      |
| Retry policy 3x/5s (future `retry`/`deezer` groups)       | spec REQ-013 / REQ-014                                                                                                                                      |
| `limit=5` search cap (future `deezer` group)              | spec REQ-001 / REQ-002; [deezer-api.md](../../specs/001-song-fingerprint-engine/contracts/deezer-api.md) §1                                                 |
| Logging config consumption                                | [logging-report.md](logging-report.md)                                                                                                                      |

**Source articles**: "Stop Hard-Coding in a Data Science Project: Use Configuration Files Instead" (https://codecut.ai/stop-hard-coding-in-a-data-science-project-use-configuration-files-instead/); Hydra docs (https://hydra.cc/docs/intro/).