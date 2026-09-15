# Contributing to GenreGuru

Welcome! GenreGuru is a greenfield, agent-driven recreation of GenreGuru — a
DSP fingerprint + song-recommendation engine (AGPL-3.0). Thanks for your
interest. Please read this before opening an issue or pull request.

## Orientation

| Where                                          | What it is                                                        |
|------------------------------------------------|-------------------------------------------------------------------|
| [`README.md`](README.md)                       | Project overview, quick start, features, tech stack               |
| [`docs/README.md`](docs/README.md)             | Documentation index (start here for docs)                         |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, runtime flow, API surface, evolution path    |
| [`docs/constitution.md`](docs/constitution.md) | Core principles, engineering standards, governance                |
| [`docs/adr/index.md`](docs/adr/index.md)       | Architecture Decision Records (how design decisions get recorded) |
| [`specs/README.md`](specs/README.md)           | Feature specifications and requirements                           |
| [`docs/ROADMAP.md`](docs/ROADMAP.md)           | Maintainer-facing backlog and direction                           |

The repo layout is documented in the README's *Project Structure* section:
`src/` standalone core library, `web/` Django app + frontend (TS sources,
esbuild, templates, Vitest tests), `config/` Hydra config tree, `tests/`
pytest suites.

## Prerequisites

- **Python 3.14** (see `.python-version`)
- **uv** ≥ 0.12 — Python package manager
- **PostgreSQL 18** — local dev database (CI pins `postgres:18`)
- **Node.js 26** — frontend toolchain (`web/`)
- **Git** with the `prek` hook manager (`uv tool install prek`)

## Setup

```bash
# install hooks first so commit conventions apply from the start
prek install

# backend: sync all extra + dev dependencies into the project venv
uv sync --all-extras --dev

# database: initialize the schema
uv run python -m genreguru.db.init_db

# frontend: install deps once
npm ci --prefix web
```

Secrets and local overrides: copy `.env.example` to `.env` and fill in real
values. Dev defaults already point at a local PostgreSQL (`postgres/postgres`
on `localhost:5432`, database `genreguru`); prod configuration is
fail-closed and requires explicit `DB_*`/`DJANGO_SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`.

## Day-to-day

Fastest shippable loop against the whole suite:

```bash
# backend tests
uv run pytest

# backend coverage (95% gate; full suite only — unit-only falls below by design)
uv run pytest --cov=genreguru --cov-report=term-missing

# frontend: lint + format + typecheck + tests (mirrors CI)
npm run --prefix web check

# frontend coverage
npm run --prefix web test:coverage

# python lint/format
ruff check --fix
ruff format --diff

# python type checking (ty)
uv run ty check
```

Coverage gates: backend `[tool.coverage.report] fail_under = 95` on the full
`--cov` suite (unit-only runs intentionally land below); frontend Vitest v8
thresholds 95/95/95/95 (statements/branches/functions/lines).

## Git hooks (prek)

Hooks are configured in `prek.toml` (a fast, drop-in alternative to
pre-commit):

| Hook                      | Stage      | What it enforces                  |
|---------------------------|------------|-----------------------------------|
| `ruff-check`              | pre-commit | `ruff check --fix`                |
| `ruff-format`             | pre-commit | `ruff format --diff`              |
| `ty`                      | pre-commit | type checking                     |
| `conventional-pre-commit` | commit-msg | Conventional Commit title + scope |
| `check-frntnd`            | pre-commit | `npm run --prefix web check`      |

Run everything manually with `prek run` (staged files) or `prek run --all-files`.

## Commit & PR conventions

Commit and PR titles follow **Conventional Commits** with a **mandatory
scope** — enforced by the prek commit-msg hook, the PR validation workflow
(`.github/workflows/pr-style.yml`), and the PR template:

```
type(scope): subject
```

Allowed types: `chore` `docs` `feat` `fix` `refactor` `style` `test`.

Good examples:

- `feat(api): add /api/catalog listing endpoint`
- `refactor(dsp): extract mfcc into its own module`
- `docs(contributing): document prek hook usage`

Branch off `main`, open a PR against `main`, keep it focused on one change,
and let a human (or the CI) review before merging. Squash-merge with a
Conventional Commit title is the default.

## Docs ship with the code

A feature PR is complete only when its documentation ships **in the same PR**:

- Changed behavior or contracts update the feature traceability/status docs
  (`specs/*/tasks.md`).
- Design decisions that change the system get an Architecture Decision Record
  (`docs/adr/`) and update `docs/ARCHITECTURE.md` where relevant.
- Public API changes update module docstrings — that is the pdoc-rendered API
  reference surface.

Reviewers enforce this: a docs/implementation mismatch is a merge blocker, not
a follow-up. The PR template's checklist encodes the same rule.

## Code style

- Python: Ruff (0.16) with pydocstyle (`D`) rules on — Google-style docstrings
  (see `docs/docstring-style-guide.md`); max complexity 10.
- Type checking: `ty` on `src/` `tests/` `web/`.
- Frontend: ESLint 10 (flat config) + Prettier 3 + TypeScript strict.
- Tests: real behavior, not mocks for its own sake; prefer parametrized,
  contract-style tests (see `tests/`).