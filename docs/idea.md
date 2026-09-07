# Idea Box — future directions, experiments, improvements

Raw backlog. Triage when planning next phases; commit ideas that get adopted
out to specs/roadmap.

## Dev experience
- Test aliases: one command for ruff (check+format) + pytest + type check
  (mypy/ty); too many separate invocations today.
- Pre-commit hook wrapping the alias above.
- CI: gate on `ruff check` + typing too (tests.yml currently runs pytest +
  frontend check; extend the pytest job).

## Testing
- Django integration tests (view + template + settings path) — that gap backfired.
- Test environment isolation: dedicated `genreguru_test` DB so dev data never
  bleeds into assertions (option B from the contract-testing discussion).

## Docs
- **Refresh quickstart, README, architecture doc, spec docs, pdoc templates** — some drifted from the implemented API.

### Documentation improvement/addition plan
1. **`CONTRIBUTING.md`** — repo root contributor guide: prerequisites (Python 3.14, uv, PostgreSQL, Node 26), setup (`uv sync`, `npm ci`), running tests (`uv run pytest`, `npm run check`), lint/type-check commands, commit conventions (conventional-pre-commit hook), branch/PR workflow, pre-commit installation.
2. **`CODE_OF_CONDUCT.md`** — open-source standard companion to the AGPL-3.0 license.
3. **README.md enhancements** — add CI status badges (tests, ruff, pdoc, coverage), Table of Contents anchor links, callout box for Known Limitations near the top, progress indicator (phase 1 done / phase 2 pending), link to live API Reference (pdoc deployed on GitHub Pages).
4. **`docs/README.md`** — index/overview of all documentation files for discoverability.
5. **`docs/API.md`** — top-level API reference page tying together pdoc output, contract specs (`contracts/search-api.md`, `contracts/deezer-api.md`), and the endpoint table from README.
6. **`docs/ARCHITECTURE.md`** — promoted top-level entry point from `001-song-fingerprint-engine/architecture.md`.
7. **`docs/DECISION_LOG.md`** (ADR log) — track why specific technologies were chosen (Django vs Flask, SQLAlchemy vs Django ORM, Hydra vs env vars), record rejected alternatives, prevent re-litigation. Already partially documented in `architecture.md` §8.
8. **`CHANGELOG.md`** — Keep-a-Changelog format tracking releases/iterations; currently Phase 1-7 passes are only in `phase_3_notes.md`.
9. **`SECURITY.md`** — secret handling, Django security headers, CSRF protection, dependency scanning (bandit).
10. **`frontend/README.md`** — frontend dev instructions: running dev server, adding tests (domain spec files in `tests/` with shared `helpers.ts`/`setup.ts` + `setupFiles`), ESLint/Prettier/Vitest config, JS architecture (DOM-free TS modules + per-page `ts/pages/*-page.ts` bootstrap, 2-click state machine, `api-config` blob pattern).
11. **`tests/README.md`** — test structure, naming conventions, TDD workflow (Constitution III), fixture usage (`conftest.py`, `factories.py`), benchmark test patterns.
12. **`config/README.md`** — Hydra config tree explanation: environment switching (`GENREGURU_ENV`), `${oc.env:...}` interpolation, feature flag gating, adding new config groups.
13. **Module docstrings** — add missing docstrings to `genreguru/config.py`, `genreguru/errors.py`, `genreguru/dto.py`, `genreguru/__init__.py` (also needs `NullHandler` per logging-report Rule 11), `fingerprint_service.py`. Required for complete pdoc API output.
14. **`docs/idea.md` → `docs/ROADMAP.md`** — convert raw backlog to structured roadmap with completed/in-progress/planned sections; integrate completed Pass 1-7 items.
15. **`docs/TODOs/` cleanup** — items folded into this file (`### README backlog`,
    `## Data`, `## Architecture`, `## ML experiments`); directory removed,
    `api.md` cross-references retargeted.
16. **Interactive tutorial / screenshot** — README "Preview/screenshot" item from Site/promo; step-by-step walkthrough showing actual terminal output and UI flow.
17. **`AGENTS.md`** at repo root — document agentic workflow conventions, available skills (`caveman`, `speckit-*`, `caveman-commit`, etc.), and project-specific AI-assisted development instructions.
18. **`notebooks/` documentation** — document purpose and usage of exploratory DSP notebooks.
19. **`docs/001-song-fingerprint-engine/` index** — `specs/README.md` or similar index listing all spec documents and their relationships.
20. **`phase_3_notes.md` → `CHANGELOG.md` migration** — migrate resolved Pass 1-7 entries from `phase_3_notes.md` into `CHANGELOG.md` entries.
21. **Docs-in-PR policy** — a feature PR ships its docs with the code: contract → traceability → status docs (`tasks.md`), `architecture.md` decision/tree rows, README/quickstart, and pdoc template purpose rows change in the SAME PR as the code. Review enforces; never land a docs/impl mismatch.

### Standards/patterns reference (one-time deep-parse)
- One-time deep-parse of the repo to extract coding standards + established
  patterns into a modular reference. Keep `AGENTS.md` thin — an index that
  points to per-domain standards files (testing, frontend ts modules,
  python/django, docs/specs workflow, do-not-touch history, error-handling/
  fail-loud philosophy). Gives future agent runs a solid, segmented reference
  instead of hunting across files for patterns — velocity, especially as the
  project scales. The modular split also maps cleanly to future skills/loops
  (each standards file ≈ a skill scope); exact file layout decided during the
  parse pass.

### README backlog (folded from docs/TODOs/README.xit)
- [ ] Capture & add app screenshots (search results + fingerprint result) under `docs/screenshots/`, reference with relative links
- [ ] Add "Try it" one-liner — single copy-paste bash block to run the whole stack
- [ ] Add real fingerprint JSON output example (e.g. `spectral_centroid`, `rms`, `mfcc` values)
- [ ] Add rendered spectrogram image with spectral centroid highlighted (DSP visualization feature)
- [ ] Add recommendations demo — before/after feature-slider tweak yielding different similar songs
- [ ] Add 8-features table: feature / what it captures / what a high value sounds like
- [ ] Add Windows & macOS setup instructions (current `export` blocks are bash-only)
- [ ] Document known limitations: 30s Deezer preview only, Deezer catalog dependency, no genre classification
- [ ] Add "Related tools / why not alternatives" positioning (Essentia, acousticDB, Chromaprint)
- [ ] Add Roadmap section
- [ ] Add Contributing section
- [ ] Expand badges: tests, coverage, ruff, uv
- [ ] Reorder README: hero → demo/screenshots → features grid → how it works → quick start → recommendation+viz → architecture → API → stack → structure → config → roadmap → contributing → license

## Frontend
- Layout/theme experiment — retro throwback look **for some layouts** (mixed aesthetics, not the whole app). Reference styles:
  - https://wildrose.space/
  - https://sweethard666.neocities.org/#
  - https://mypillowfort.net/?z=/tuts/
  - https://www.cameronsworld.net/
  - https://www.pedrobelleza.com/
  - https://morisinc.net/
  - https://beigeforce.com/
  - https://www.cozyeating.app/
- Song preview card before confirm: album art, artist, provider icon.
- Multi-artist previews — a song can have multiple artists, but the preview
  shows only Deezer's main `artist` (track `contributors` are dropped by the
  client; `Song.artist` is a single String(255); contracts expose one
  `artist {id,name}`). Fix: carry the full artist list and truncate long ones
  with a trailing `…`. Requires a data-model.md change (Song schema) plus the
  Deezer client mapping and deezer-api/search-api contracts.
- No-preview edge cases (missing/invalid Deezer preview URL).
- Error toasts — small, dismissable, fade-from-below, bottom-right; shown on any
  error. Expandable: later cover non-blocking events (fingerprint stored, slow
  network, background rechecks) instead of status-line-only copy. Needs a
  `role="status"`/aria-live source element for screen readers.
- Farm favicon: an inline SVG `data:` URI in a `<link rel="icon">` kills the
  `/favicon.ico` 404 with zero asset files/browser requests.
- Add a `<meta name="description">` snippet — a non-functional page summary
  used in search-result listings and preview cards (browser tabs show the
  `<title>`; the description is what external surfaces quote).

## Data
- Backfill a large catalogue for dev/prod (e.g. Billboard chart feeds) so the
  fingerprint engine has real volume to chew on.
- Use Deezer [global parameters](https://developers.deezer.com/api/parameters)
  and [optional search parameters](https://developers.deezer.com/api/search#:~:text=Optionnal%20Parameters) on the search client.

## Infrastructure
- Rename `frontend/` → `web/` to resolve confusion (Django project root named
  "frontend"). Blast radius: `.gitignore` (~5 entries), README tree+commands,
  architecture.md paths, quickstart.md paths, CI `tests.yml` working-directory,
  any `cd frontend` in scripts/docs, `pyproject.toml` tool configs.

## Architecture
- Centralize cross-functional/cross-language/cross-file constants into a single
  source/config, e.g. feature labels now live on the `Feature` enum, not in JS
  or per-file literals. Audit other duplicated values (units, message strings,
  thresholds, URL "know-how") for the same treatment so a change lands in one
  place and crosses the frontend/backend boundary through the `#api-config` blob.
- Explicit instance of the above: `_deezer = DeezerSearchClient()` in
  `fingerprint_app/views.py` uses constructor defaults (search URL, limit,
  timeouts, retry budget) rather than `cfg`. The deezer search tuning should
  flow from config like the rest of the cross-boundary constants.
- `genreguru_web/runtime.py::init_runtime()` guards one-time init with a bare
  module-global `_initialized`. Fine today (entrypoints call it at import,
  single-threaded), but under ASGI concurrency or forked workers that is a
  race. Fix sketch: hold a module-level `threading.Lock`, do the create-engine
  + logging-setup inside it after re-checking `_initialized`
  (double-checked), or make `LoggingManager.setup` tolerant of re-invocation.
- Enforce rate-limiting & abuse-prevention for the internal search API (per
  CHK024 in `api.md` / `search-api.md`).

## Product
- Song recommendations from fingerprint distance metric (nearest neighbors on
  stored vectors).

## ML experiments
- Setup MLFlow for experiment tracking.

## Site/promo
- Preview/screenshot in README for readability.
- GitHub Pages site: a repo hosts one `github.io` site; an org can host many
  (so this could live on a separate repo, or on this one at `docs/`).
- Demo video once the product story settles.