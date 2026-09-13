# ADR-0000: Use architecture decision records

- **Status**: Accepted
- **Date**: 2026-09-12

## Context

Technology and structural choices (Django vs Flask, SQLAlchemy vs the
Django ORM, Hydra vs env vars, collapse policy, deployment direction) were
being re-explained in prose or re-litigated because the rationale had no
stable home. `docs/ARCHITECTURE.md §8` collects some but is a feature doc
and does not scale to cross-cutting or deferred decisions.

## Decision

We will record architecturally significant decisions as Architecture
Decision Records (ADRs), one decision per file, in `docs/adr/`, using the
[Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
(title, Context, Decision, Status, Consequences). Files are numbered
monotonically with a hyphenated imperative name. Statuses are *proposed*
(under discussion), *accepted* (agreed), or *superseded* (replaced, with a
link to the replacement). A rejected decision is recorded as a record with
status *rejected* when it needs to stay answerable. Decisions already
documented elsewhere are backfilled in pointer style — each record carries
the decision summary plus a reference to the source of detail, never a
duplication of the source.

## Consequences

- Previous decisions stop being re-examined by default; context is
  preserved for future stewards.
- Every architecturally significant choice carries a small authoring
  cost and a review step (ADR ships in the same PR as the code it enables).
- Trivial/local implementation choices do not warrant an ADR.

## References

- [`docs/ARCHITECTURE.md §8`](../ARCHITECTURE.md) — decision table that
  seeded ADR-0001..0007.
- `docs/ROADMAP.md` Infrastructure — deployment decisions D1–D5 that seeded
  ADR-0008..0012.