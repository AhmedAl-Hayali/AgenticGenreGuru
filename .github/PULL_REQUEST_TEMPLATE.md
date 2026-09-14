## What & why

<!-- One or two sentences: what this PR changes and why. If it fixes an issue, add "Closes #NN". -->

## Type

<!--- pick one, keep the same format CI requires (type(scope): subject) -->

- `feat(scope)`: new capability
- `fix(scope)`: bug fix
- `refactor(scope)`: internal change, no behavior change
- `docs(scope)`: documentation only
- `test(scope)`: tests only
- `chore(scope)`: tooling/maintenance
- `style(scope)`: formatting, no logic change

## Title

`type(scope): subject` — CI validates it (`.github/workflows/pr-style.yml`).
The prek `conventional-pre-commit` hook enforces the same form locally.

## Checklist

Docs ship with the code — a docs/implementation mismatch is a merge blocker.

- [ ] Behavior/contract changes reflected in the feature docs (`specs/*/tasks.md`)
- [ ] Design-affecting changes recorded (new/updated ADR in `docs/adr/`) and reflected in `docs/ARCHITECTURE.md`
- [ ] Public API changes reflected in module docstrings (pdoc-rendered surface)
- [ ] README/quickstart touched where user-facing behavior changed
- [ ] Tests pass: Ruff, Tests, PR validation workflows green
- [ ] `git status` clean of stray/unrelated files

## Notes for reviewers

<!-- Anything that needs judgement: tradeoffs, deferred follow-ups, risk areas. -->