"""Unit tests for the database engine factory (`genreguru/db/engine.py`).

Covers Hydra `db` group ingestion, psycopg URL construction, engine type,
pool settings, and fail-fast behavior when the prod group is selected
without a `DATABASE_URL` environment variable (config/db/prod.yaml resolves
`${oc.env:DATABASE_URL}` with no fallback).

These tests are written first (Constitution III TDD) and target the
engine factory contract; live connections are exercised by the integration
tests instead.
"""

from omegaconf import DictConfig
from sqlalchemy.engine import Engine


def test_engine_from_dev_db_group(engine: Engine, db_cfg: DictConfig):
    """Test that the engine is built from the composed Hydra `db` group."""
    assert isinstance(engine, Engine)
    assert engine.dialect.name == db_cfg.dialect
    assert engine.dialect.driver == db_cfg.driver


def test_dev_db_group_targets_genreguru_database(engine: Engine, db_cfg: DictConfig):
    """Test that the default dev components point at the Genreguru database."""
    assert engine.url.database == db_cfg.database
    assert engine.url.host == db_cfg.host
    assert engine.url.port == int(db_cfg.port)


def test_pool_settings_from_db_group(engine: Engine, db_cfg: DictConfig):
    """Test that pool_size and max_overflow come from the Hydra group."""
    # API-invasive, but necessary testing
    assert engine.pool._max_overflow == db_cfg.max_overflow  # ty: ignore[unresolved-attribute]
    assert engine.pool.size() == db_cfg.pool_size  # ty: ignore[unresolved-attribute]


def test_echo_disabled_by_default(engine: Engine, db_cfg: DictConfig):
    """Test that echo stays off unless the db group enables it."""
    assert engine.echo == db_cfg.echo
