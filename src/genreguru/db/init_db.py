"""Table-creation entrypoint: `python -m genreguru.db.init_db`.

Creates all tables declared on the SQLAlchemy `Base` against the active
Hydra `db` group. Safe to rerun without error (idempotent). Fail-fast on
servers older than PostgreSQL 18, whose native `uuidv7()` the data model
depends on (data-model.md — IDs are generated server-side by `uuidv7()`).

Prerequisites
-------------
- PostgreSQL 18+ server required (native `uuidv7()` column defaults).
  Earlier versions will abort with a logged error before any DDL
  is executed.

Usage
-----
- `python -m genreguru.db.init_db` — create tables (idempotent).
- `create_all_tables(engine)` — programmatic entry point.

Logging contract (docs/001-song-fingerprint-engine/logging-report.md §T010):
- INFO: table-creation start, completion (with table count),
  idempotent no‑op.
- `logger.exception`: on connection or DDL error.
- PG version pre-check aborts with `logger.error` before any DDL.

Exit codes
----------
- 0: tables created (or verified) successfully.
- 1: unrecoverable error (PG version, connection failure, DDL error).
"""

import logging
import sys

import hydra
from omegaconf import DictConfig
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable

from genreguru.db import models as _models  # noqa: F401  (register tables on Base)
from genreguru.db.base import Base
from genreguru.db.engine import create_engine
from genreguru.gglogging import LoggingManager

logger = logging.getLogger(__name__)

MIN_PG_MAJOR = 18
"""Minimum PostgreSQL major version required (native `uuidv7()`)."""


def _dry_run():
    """Log the generated DDL without executing against the database.

    Useful for CI/CD pipelines that want to verify the schema before
    applying it.
    """
    logger.info("dry-run mode: logging generated DDL only")

    for table in Base.metadata.sorted_tables:
        logger.info("CREATE TABLE %s;\n%s", table.name, str(CreateTable(table)))


def health_check(engine: Engine):
    """Confirm the database connection is alive before any DDL.

    Args:
        engine: SQLAlchemy engine to probe.

    Raises via logger.exception if the connection cannot be established
    or the SELECT 1 query fails.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("engine health-check failed; aborting DDL")
        raise


def _server_major(engine: Engine) -> int:
    """Return the connected server's major version (e.g. 18)."""
    return engine.dialect.server_version_info[0]  # ty: ignore[not-subscriptable]


def verify_pg_version(engine: Engine):
    """Fail-fast: verify the server is PostgreSQL 18+.

    Args:
        engine: SQLAlchemy engine whose server version to inspect.

    Raises RuntimeError if the server major version is older than PGSQL18.
    """
    major = _server_major(engine)
    if major < MIN_PG_MAJOR:
        logger.error(
            "unsupported postgres major version %d (require >= %d)",
            major,
            MIN_PG_MAJOR,
        )
        raise RuntimeError(
            f"PostgreSQL {major} detected; {MIN_PG_MAJOR}+ required (native uuidv7())",
        )


def create_all_tables(engine: Engine):
    """Create every table on `Base` if they do not already exist.

    Idempotent: `Base.metadata.create_all` does not raise if tables
    already exist; it is a no-op for those tables.

    Args:
        engine: Engine backed by psycopg, built from the Hydra `db` group.
    """
    logger.info("creating database tables")
    Base.metadata.create_all(engine)
    table_names = sorted(Base.metadata.tables)
    logger.info(
        "database tables ready; created_or_verified=%d (%s)",
        len(table_names),
        ", ".join(table_names),
    )


@hydra.main(config_path="../../../config", config_name="config")
def main(cfg: DictConfig) -> None:
    """Compose config, claim logging, and create all tables.

    Workflow:
    1. Initialise the `LoggingManager` per the `logging` config group.
    2. Log the generated DDL if `cfg.db.dry_run` is set, then exit
       successfully (exit code 0) without touching the database.
    3. Build the SQLAlchemy engine from the composed Hydra `db` group.
    4. Run a connection health‑check.
    5. Fail‑fast if the PostgreSQL server major version is < 18.
    6. Idempotently create any missing tables.
    7. Dispose the engine's connection pool (before logging teardown).

    Exits via `sys.exit(1)` on any failure; returns normally (exit code 0)
    on success. `@hydra.main` discards this function's return value on the
    CLI path, so the failure exit code is raised as `SystemExit` directly.
    """
    try:
        with LoggingManager() as manager:
            manager.setup(cfg.logging)

            if cfg.db.dry_run:
                _dry_run()
                return

            engine = create_engine(cfg.db)
            try:
                health_check(engine)
                verify_pg_version(engine)

                create_all_tables(engine)
            finally:
                engine.dispose()
    except Exception:
        logger.exception("Error encountered during table creation")
        sys.exit(1)


if __name__ == "__main__":
    # `cfg` captured passed @hydra.main(...)
    raise SystemExit(main())
