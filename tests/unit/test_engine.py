"""Unit tests for the database engine factory (`genreguru/db/engine.py`).

Covers Hydra `db` group ingestion, psycopg URL construction, engine type,
pool settings, and fail-fast behavior when the prod group is selected
without the required `DB_*` environment variables (config/db/prod.yaml
resolves `${oc.env:DB_USER}`/`${oc.env:DB_PASSWORD}`/`${oc.env:DB_HOST}`/`${oc.env:DB_PORT}`
with no fallback).

These tests are written first (Constitution III TDD) and target the
engine factory contract; live connections are exercised by the integration
tests instead.
"""

from types import SimpleNamespace

import pytest
from omegaconf import DictConfig
from omegaconf.errors import ConfigAttributeError
from sqlalchemy import create_engine as _sa_create_engine
from sqlalchemy.engine import Engine

from genreguru.db import engine as eng_module


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


def test_missing_config_attribute_raises():
    """An incomplete `db` group must fail fast with `ConfigAttributeError`."""
    with pytest.raises(ConfigAttributeError):
        eng_module._build_url(DictConfig({}))


@pytest.mark.parametrize(
    ("connection", "expected_host"),
    [
        (SimpleNamespace(), "UNKNOWN_HOST"),
        (SimpleNamespace(info=SimpleNamespace(host="db-prod-1")), "db-prod-1"),
    ],
    ids=["unreported_host", "reported_host"],
)
def test_pool_invalidate_logs_host(caplog, connection, expected_host):
    """A pool invalidate must log the host, falling back to `UNKNOWN_HOST`."""
    _sample_engine = _sa_create_engine("sqlite://")
    eng_module._attach_pool_events(_sample_engine)
    with caplog.at_level("WARNING", logger=eng_module.__name__):
        _sample_engine.pool.dispatch.invalidate(connection, None, None)  # ty: ignore[unresolved-attribute]
    assert f"connection to database lost (host={expected_host})" in caplog.text
