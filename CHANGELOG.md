# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `CONTRIBUTING.md` — contributor guide (orientation, prerequisites, setup, tests,
  prek hooks, commit conventions, docs-ship-with-code rule).
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1.
- `SECURITY.md` — vulnerability reporting, supported versions, security posture.
- `CHANGELOG.md` — this file (Keep a Changelog format).
- `.github/PULL_REQUEST_TEMPLATE.md` — PR template encoding the
  docs-ship-with-code checklist.

### Changed

- Docs navigation skeleton: `docs/README.md` + `specs/README.md` directory
  indexes; `docs/ARCHITECTURE.md` promoted out of the feature folder; `docs/adr/`
  for the deployment/hardening decisions (D1–D5); `docs/API.md` authoritative API
  surface; `docs/idea.md` moved to `docs/ROADMAP.md`.
- README refresh: stacked tech/coverage/license badges (live Codecov per-flag
  coverage via `636ef5f`, `67d4b90`, `d100d21`), Table of Contents, `## Project
  Status` progress indicator, Known Limitations callout, Learn More links to
  `CONTRIBUTING.md`/`SECURITY.md`/`CHANGELOG.md`.
- `docs/ROADMAP.md` reorganized: completed docs work moved to Completed, planned
  items pruned of `*shipped*` flags.
- README test badges + `## Tests` section: truthful CI-state shields (pytest,
  Vitest, Ruff, pdoc) + headlined suite counts (235 pytest / 115 Vitest).