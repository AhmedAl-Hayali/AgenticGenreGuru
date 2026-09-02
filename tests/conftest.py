"""Shared pytest fixtures.

Provides session-scoped `db_cfg`, `engine`, and `db_schema`, and
function-scoped `db_session`, `factory_session`, and `django_client`.
Fixtures share module-level `get_config()` (lru-cached, env-frozen at first call).
`db_session` uses SAVEPOINT isolation; no test data persists.
`factory_session` configures the shared scoped session for FactoryBoy
factories and removes it on teardown.
`db_schema` creates the ORM tables (`songs`, `song_fingerprints`) on the
live PostgreSQL engine once per session.
The autouse `_no_sleep` kills the 5s Deezer retry delay for the retry suites.
"""

from collections.abc import Generator

import pytest
from django.test import Client
from omegaconf import DictConfig
from sqlalchemy import Engine

from genreguru.config import get_config
from genreguru.db.engine import create_engine, get_session_factory
from genreguru.db.repositories import SongRepository
from tests.factories import sc_session
from tests.http_stubs import no_sleep


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


@pytest.fixture(scope="session")
def db_schema(engine) -> None:
    """Create the ORM tables on PostgreSQL once per test session."""
    from genreguru.db import models  # noqa: F401  registers tables on Base.metadata
    from genreguru.db.base import Base

    Base.metadata.create_all(engine)


@pytest.fixture()
def db_session(engine):
    """Yield a SAVEPOINT-isolated session; commits never reach the database."""
    with engine.connect() as conn:
        transaction = conn.begin()
        session_factory = get_session_factory()
        session = session_factory(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            transaction.rollback()
            session.close()


@pytest.fixture()
def repo(db_session) -> SongRepository:
    """Return a `SongRepository` bound to the SAVEPOINT-isolated test session."""
    return SongRepository(db_session)


@pytest.fixture()
def factory_session(engine):
    """Configure the shared scoped session for this test; remove on teardown.

    Request this fixture in any test that uses FactoryBoy factories:

        def test_create_song(factory_session):
            song = SongFactory.create()
            assert song.id is not None

    Not needed for tests that only use `db_session` directly.
    """
    sc_session.configure(bind=engine)

    yield sc_session

    sc_session.remove()


@pytest.fixture()
def django_client() -> Client:
    """Fresh `django.test.Client` for exercising Django views."""
    return Client()


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch) -> None:
    """Eliminate the 5s retry delay so retry tests don't sleep between attempts.

    WARNING: `time` is a process-global singleton, so patching
    `genreguru.deezer._retry.time.sleep` swaps `time.sleep` suite-wide. Only
    `_retry.py` (via `import time` + attribute access) consumes it today; any
    future test that needs a real sleep must not rely on this autouse no-op.
    """
    no_sleep(monkeypatch, "genreguru.deezer._retry")
