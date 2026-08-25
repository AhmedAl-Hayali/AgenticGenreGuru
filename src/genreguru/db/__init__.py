"""SQLAlchemy database engine, session factories, and ORM models.

Submodules:

- `.base` — Declarative base, `.base.TimestampedMixin`, `.base.UuidMixin`.
- `.engine` — Engine creation and session-factory lifecycle.
- `.init_db` — Idempotent table-creation entrypoint (`python -m genreguru.db.init_db`).
- `.models` — `.models.Song` and `.models.SongFingerprint` ORM models.
"""
