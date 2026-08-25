"""SQLAlchemy database engine, session factories, and ORM models.

Submodules:

- `engine` — Engine creation and session-factory lifecycle.
- `models` — `Song` and `SongFingerprint` ORM models.
- `base` — Declarative base, `TimestampedMixin`, `UuidMixin`.
- `init_db` — Idempotent table-creation entrypoint (`python -m genreguru.db.init_db`).
"""
