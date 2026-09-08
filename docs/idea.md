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
- **Raw-array test layer** — `tests/unit/test_audio_features.py` mostly pins the
  *collapsed* scalar layer; the extract/collapse split's raw ndarray layer stays
  largely untested (only mfcc `(20, n_frames)` shape + finiteness are covered).
  Still to add:
  - **Raw shape contract** — parametrized per `extract_<feature>` on the
    1s/22050Hz sine: temporal features `(1, n_frames)` (centroid, rms,
    bandwidth, flatness, rolloff, zcr), contrast `(7, n_frames)`, mfcc
    `(20, n_frames)`; `n_frames` consistent with `n_fft=2048`, `hop=512`,
    center=True.
  - **Raw dtype** — spectral outputs float32 (librosa default); assert no
    object/void dtype.
  - **Raw finiteness** — `np.all(np.isfinite(arr))` per feature on sine,
    silent, low-energy inputs (mirrors the collapsed finite checks at raw
    level).
  - **`collapse_feature(arr, name)` == `float(np.mean(raw))`** — exactly, no
    hidden transforms.
  - **`collapse_features` round-trip** — equals `collapse_feature(arr, f)`
    applied individually; keys match the `Feature` enum; all values Python
    `float`.
  - **Centroid reuse invariant** — bandwidth equals
    `spectral_bandwidth(S=mag, sr=sr, centroid=raw["spectral_centroid"])`
    (guards the shared-centroid optimization against regression).
  - **Collapse-policy independence** — adding/replacing a `collapse_<feature>`
    must not change `extract_<feature>` output (contract of the split).
  - **Empty / zero-length input** — `extract_<feature>` behavior (warn/raise?)
    is untested for empty arrays.

## Docs
- **Refresh quickstart, README, architecture doc, spec docs, pdoc templates** — some drifted from the implemented API.
- **API reference look-and-feel** — pdoc's default template is functional but
  dated; the live reference is a public-facing surface (README badge → GH
  Pages). Options, cheapest first: (1) pdoc already ships a theme toggle —
  check current template/`pdoc themes` for a dark-mode option and CSS
  overrides before touching anything else; (2) drop a custom CSS/JS embed via
  pdoc's `--template-directory` / custom `head.mako` for branding; (3) if
  pdoc still underwhelms, switch generators — candidates that are equally
  plug-in-and-run against docstrings/modules: `mkdocstrings` (Material for
  MkDocs, themable dark mode, search), `Sphinx + sphinx-rtd-dark-mode` or
  `Furo` theme (heavier config). Keep the bar: near-zero migration cost +
  equally productive output (module/class/function docstrings, signatures,
  source links); pdoc deployment already lives in CI `docs.yml` + `.github/
  workflows`, keep that path. Future-proof: pick a theme behind a build-time
  config so the docs site and the deployed artifact share one source.

### Documentation improvement/addition plan
1. **`CONTRIBUTING.md`** — repo root contributor guide: prerequisites (Python 3.14, uv, PostgreSQL, Node 26), setup (`uv sync`, `npm ci`), running tests (`uv run pytest`, `npm run check`), lint/type-check commands, commit conventions (conventional-pre-commit hook), branch/PR workflow, pre-commit installation.
2. **`CODE_OF_CONDUCT.md`** — open-source standard companion to the AGPL-3.0 license.
3. **README.md enhancements** — add CI status badges (tests, ruff, pdoc, coverage), Table of Contents anchor links, callout box for Known Limitations near the top, progress indicator (phase 1 done / phase 2 pending), link to live API Reference (pdoc deployed on GitHub Pages).
4. **`docs/README.md`** — index/overview of all documentation files for discoverability.
5. **`docs/API.md`** — top-level API reference page tying together pdoc output, contract specs (`contracts/search-api.md`, `contracts/deezer-api.md`), and the endpoint table from README.
6. **`docs/ARCHITECTURE.md`** — promoted top-level entry point from `001-song-fingerprint-engine/architecture.md`.
7. **`docs/DECISION_LOG.md`** (ADR log) — track why specific technologies were chosen (Django vs Flask, SQLAlchemy vs Django ORM, Hydra vs env vars), record rejected alternatives, prevent re-litigation. Already partially documented in `architecture.md` §8.
8. **`CHANGELOG.md`** — Keep-a-Changelog format tracking releases/iterations; phase/pass history currently only in git history (the old `phase_3_notes.md` scratch file has been discarded).
9. **`SECURITY.md`** — secret handling, Django security headers, CSRF protection, dependency scanning (bandit).
10. **`web/README.md`** — web dev instructions: running dev server, adding tests (module-mirrored test files in `tests/` — `api.test.ts`/`render.test.ts`/`page-controller.test.ts` cover the `ts/` modules, `bootstrap.test.ts` the boot layer, `a11y.test.ts` cross-cutting — with shared `helpers.ts`/`setup.ts`), ESLint/Prettier/Vitest config, JS architecture (DOM-free TS modules + per-page `ts/pages/*-page.ts` bootstrap, 2-click state machine, `api-config` blob pattern).
11. **`tests/README.md`** — test structure, naming conventions (module-mirrored frontend files; `dto.ts`/`messages.ts`/`errors.ts` intentionally fileless — covered transitively via their callers), TDD workflow (Constitution III), fixture usage (`conftest.py`, `factories.py`), benchmark test patterns.
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
20. **Docs-in-PR policy** — a feature PR ships its docs with the code: contract → traceability → status docs (`tasks.md`), `architecture.md` decision/tree rows, README/quickstart, and pdoc template purpose rows change in the SAME PR as the code. Review enforces; never land a docs/impl mismatch.
21. **Per-folder README strategy** — GitHub renders a folder's `README.md` as
    its directory landing page; give the 7 content folders one (`src/`,
    `web/`, `tests/`, `config/`, `specs/`, `docs/`, `.github/`) so the
    root README headline stays clean and each folder reads in full when
    browsed. Folds in items #4, #10, #11, #12, #19. When implementing:
    collapse the root `Project Structure` prose (README.md:246-270) to
    one-line link pointers + add them to `Learn More`; keep each README small
    and factual (15-40 lines, same shape: purpose → layout → entry points →
    run/verify → links); leave empty/artifact folders (`data/`, `models/`,
    `reports/`, `references/`, `notebooks/`, `outputs/`, `logs/`)
    README-less; ship README changes in the same PR as the feature (#20).

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
- **Accessibility testing beyond unit context** — `web/tests/a11y.test.ts`
  pins keyboard/click + ARIA contract tests, but there's no programmatic WCAG
  audit. Add axe-core scans in Vitest/jsdom (cheap, fast) and/or a Playwright
  end-to-end pass on the served app; pair with a manual WCAG checklist step
  (keyboard-only walkthrough, focus order/visibility, contrast, touch targets,
  aria-live). Error-toasts bullet above already calls out the missing
  `role="status"`/aria-live source — fold audits in when that lands.
- **Design-tool integration (Figma)** — introduce a component library + design
  tokens (color/type/spacing) in Figma, exported to CSS custom properties the
  UI consumes; single source of truth instead of ad-hoc CSS. Evaluate a tokens
  pipeline (e.g., style-dictionary) before styles multiply.
- **Frontend test-tooling review** — survey the JS ecosystem (what Mocha & Jest
  are vs the current Vitest 5 + jsdom setup; where Playwright/axe add value)
  and record the decision. No migration for its own sake — Vitest is working;
  gain would be layered e2e/a11y coverage, not a runner swap.
- **Lazy loading audit** — today one bundled `app.js` serves the index page.
  As `pages/` and features grow: per-page/dynamic `import()` splitting,
  `defer`/`async` script loading, static-asset caching (hash-named files), and
  lazy-loading song preview metadata/artwork when the candidate is confirmed.
- **Draft + audit non-functional requirements** — capture frontend NFRs as
  explicit budgets and contracts: performance (FCP/TTI, bundle size), load-time
  budget, accessibility baseline, responsive breakpoints, browser matrix,
  offline/resilience behavior. Audit on a schedule: measure → record → fix.
  Today NFRs are implicit; spec them before they bite.
- **HCI principles — document, audit, record violations** — name the heuristics
  the UI is designed around (error prevention: 2-click select/confirm state
  machine; visibility of system status: `aria-live` status line; consistency;
  feedback/copy) and how to verify them. Define a per-heuristic walkthrough
  (e.g., Nielsen's 10) to find violations; keep a running HCI-violation log
  (file/component + heuristic) feeding the backlog, not a one-off review.

## Data
- Backfill a large catalogue for dev/prod (e.g. Billboard chart feeds) so the
  fingerprint engine has real volume to chew on.
- Use Deezer [global parameters](https://developers.deezer.com/api/parameters)
  and [optional search parameters](https://developers.deezer.com/api/search#:~:text=Optionnal%20Parameters) on the search client.

## Audio / DSP

### N-section collapse (`feature_collapse.py`) — PENDING REVIEW

Design sketched, not approved; no code changed (`collapse_feature` still
returns a scalar, `collapse_features` a `dict[Feature, float]`). Don't implement
until questions [B]/[C] below settle.

Motivation: `data-model.md` line 45 — V1 collapses each feature to one scalar;
"future versions will support lower downsampling rates to retain temporal
dynamics." Proposal: collapse produces **N section scalars** per feature
(intro/middle/outro dynamics) via a pluggable split rule. Scope: collapse module
+ tests + minimal caller wiring; no DB/schema change.

Confirmed decisions: (1) unified always-sections API — scalar path is a slice of
the 1-section result; (2) return type `dict[Feature, np.ndarray]`, each key
shape `(N,)`; (3) sections may be unequal length in the future — split strategy
pluggable, not hardcoded; (4) collapse module only.

Design:
- `SectionPlan.split(n_frames) -> list[np.ndarray]` (frame index groups);
  `EvenFrameSections(n_sections)` clamps `max(1, min(n, n_frames))` and uses
  `np.array_split` (15/15/14 for n=44,N=3). Future `DurationSections`, adaptive,
  weighted strategies implement `split`; core only depends on `.split`.
- `_mean_per_section(feature, n_sections, section_plan=None)` → shape `(N,)` via
  `np.mean(feature[..., g])` per group (averages leading non-time axes for
  contrast/mfcc); **N=1 == `np.mean(feature)` exactly** (backward compatible).
- API: `collapse_feature(arr, Feature.X, n_sections=1, section_plan=None)`
  shape `(N,)`; `collapse_features(d, n_sections=1) -> dict[Feature, ndarray]`;
  `collapse_features_to_scalars(d) -> dict[Feature, float]` preserves the
  current float contract. The 8 `collapse_*` aliases were already dropped in the
  `Feature`-enum refactor — fully generic `collapse_feature` only ([A] resolved).
- Caller wiring: `fingerprint_service.py` → `collapse_features_to_scalars`
  (still stores floats, DB untouched); `feature_extract.py` docstring scalar
  reference updated.
- Tests: scalar fixtures → `collapse_features_to_scalars` / shape-`(1,)`; new
  `n_sections=8` → 8 keys × shape `(8,)`; N=1 equals `np.mean(feature)`; section
  values within feature min/max; `n_sections > n_frames` clamps; custom
  unequal-length `SectionPlan` sum-of-lengths == n_frames; scalar view equals
  pre-refactor `dict[str, float]`.

Open questions:
- **[B] N=1 return type** — unified `collapse_features(d, N=1)` returns shape-
  `(1,)` arrays, breaking the current `dict[str, float]` contract. Confirm the
  `collapse_features_to_scalars` split vs changing `collapse_features` outright.
- **[C] Unequal-length semantics** — `np.array_split` gives 15/15/14 for
  n=44,N=3; confirm contiguous frame groups are the right sectioning (vs
  equal-duration / overlapping later).

Behavioral output (sine, N=3): frame groups [(1,15),(16,30),(31,44)]; rms
0.34686 → [0.34352, 0.35352, 0.34332]; spectral_contrast 18.7347 → [18.1115,
19.9331, 18.1185] (mid-track peak retained); mfcc −19.7905 → [−19.0115,
−21.4269, −18.8719].

Verify when implementing (not yet run): `ruff check` + `ruff format --check`
clean; `uv run pytest tests/unit -q` all existing + new green.

## Infrastructure
- **Done — `frontend/` → `web/` rename** (resolves the Django project root
  named "frontend" confusion). Executed: dir moved + `.gitignore` paths,
  README tree/commands, architecture.md + config-report.md paths,
  quickstart.md paths, CI `tests.yml`/`docs.yml` PYTHONPATH +
  working-directory + artifact paths, prek.toml hook, pyproject.toml tool
  configs. Identifiers renamed too: `tests.yml` job/artifact →
  `web`/`web-coverage`, package `genreguru-frontend` → `genreguru-web`.
  Historical specs (`plan.md`, `tasks.md`) left as-recorded with a mapping
  note; prose "frontend" kept as the abstraction/layer name.
- **Deployment & containerization** — ship the app to a prod-grade environment.
  Directions settled (decisions D1–D5; each records its future-proof path so a
  later scale-up slots in with minimal churn). None implemented yet.
  - **D1 — Deploy target: local prod-sim first, cloud later.** `Dockerfile` +
    `compose.yaml` (web + postgres + TLS reverse proxy) mimicking prod wiring
    locally via `GENREGURU_ENV=prod` config groups. Future-proof: the same
    image deploys to a PaaS (Fly.io/Render/Railway — managed TLS, deploy from
    git) behind a GH Actions build→registry→`fly deploy`/`render deploy`
    workflow; does not change when multi-node arrives.
  - **D2 — App server: Gunicorn (WSGI, sync workers), no `--preload`.**
    Views are sync today (`fingerprint_app/views.py`); wsgi.py + asgi.py
    entrypoints exist, ASGI path unused. Per-worker import runs
    `runtime.init_runtime()` per process (safe); `--preload` would share one
    psycopg3 engine/pool across forked fds (risk — keep off). Future-proof:
    uvicorn/granian ASGI when async views land; `--threads` for IO-heavy
    paths; multi-replica needs the `runtime.init_runtime()` `threading.Lock`
    fix (Architecture bullet) + per-replica `create_engine` (already
    per-process).
  - **D3 — Static: Whitenoise in-container.** esbuild output
    (`fingerprint_app/static/.../app.js`) is gitignored → frontend must build
    inside the image (Node 26 builder stage); serve via collectstatic +
    whitenoise. Future-proof: `ManifestStaticFilesStorage` cache-busting;
    object storage/CDN (MinIO/S3) when media/uploads grow; no settings churn
    at either step.
  - **D4 — DB reliability: compose PG18 + named volume + healthcheck +
    release-step schema job + `pg_dump` backup.** Native `uuidv7()` requires
    PG18+ (CI already pins `postgres:18`). Schema via one-off `migrate`
    compose service running `uv run python -m genreguru.db.init_db`, gated
    `service_completed_successfully`; no racing on-boot mutations.
    Future-proof: swap db service for managed Postgres (Fly/Render/Neon) with
    PITR — same `DB_*` env contract; pgbouncer/read-replica when load grows;
    backups escalate pg_dump → WAL/PITR.
  - **D5 — Scale/hardening: single instance, standard hardening.** prod
    settings already `DEBUG=0`, secure cookies, HSTS, fail-closed
    `DJANGO_ALLOWED_HOSTS`/`DJANGO_SECRET_KEY`/`DB_*` via env. Add
    `SECURE_PROXY_SSL_HEADER` (TLS-terminating proxy) since
    `secure_ssl_redirect: true` would otherwise loop behind the proxy.
    Rate-limiting (CHK024) stays deferred. Future-proof: multi-replica, WAF/
    ingress, secrets manager, pool-size/`CONN_MAX_AGE` tuning per replica.
  Still open (verify when implementing): Gunicorn wheels on Python 3.14
  (fallback uvicorn/granian if unsupported — D2 keeps the slot, driver
  swappable); prod logging `file_all` handler writes
  `logs/genreguru.log.jsonl` — container path is ephemeral, pick stdout-only
  override vs mounted volume; `uv.lock` is gitignored — commit it or
  `uv sync --no-lock` for fresh clones; whether Deezer preview URLs need a
  proxy/allowlist for CORS in prod.

## Architecture
- Centralize cross-functional/cross-language/cross-file constants into a single
  source/config, e.g. feature labels now live on the `Feature` enum, not in JS
  or per-file literals. Audit other duplicated values (units, message strings,
  thresholds, URL "know-how") for the same treatment so a change lands in one
  place and crosses the frontend/backend boundary through the `#api-config` blob.
- Explicit instance of the above: `_deezer = DeezerClient()` in
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
- **Present testing on GitHub** — make the test suite visible to visitors:
  live README badges (vitest check, coverage %, ruff, pdoc) wired to CI, a
  "Tests" section with the breakdown by layer (frontend module suites —
  api/render/page-controller/bootstrap + cross-cutting a11y — and backend
  pytest families), and test-stat reporting
  (coverage % + test counts posted as CI artifacts/badges — or Codecov/
  Coveralls). Deep breakdown lives in `tests/README.md` (Docs #11); the root
  README shows headline numbers.