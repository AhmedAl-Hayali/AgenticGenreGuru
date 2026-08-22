"""Shared pytest fixtures.

Provides session-scoped `db_cfg`, `engine`, `db_session`, and `django_client`.
Fixtures share module-level `get_config()` (lru-cached, env-frozen at first call).
`db_session` uses SAVEPOINT isolation; no test data persists.
"""

from collections.abc import Generator

import pytest
from omegaconf import DictConfig
from sqlalchemy import Engine

from genreguru.config import get_config
from genreguru.db.engine import SessionLocal, create_engine


@pytest.fixture(scope="session")
def db_cfg() -> DictConfig:
    """Compose the active Hydra `db` group once per test session."""
    cfg = get_config()
    return cfg.db


@pytest.fixture(scope="session")
def engine(db_cfg) -> Generator[Engine]:
    """Build the shared SQLAlchemy engine backed by psycopg (once per session)."""
    eng = create_engine(db_cfg)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def db_session(engine):
    """Yield a SAVEPOINT-isolated session; commits never reach the database."""
    with engine.connect() as conn:
        transaction = conn.begin()
        session = SessionLocal(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture()
def django_client():
    """Fresh `django.test.Client` for exercising Django views."""
    from django.test import Client

    return Client()
