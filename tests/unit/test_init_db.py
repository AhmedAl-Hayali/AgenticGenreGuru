"""Unit tests for `genreguru.db.init_db` orchestration and failure branches.

`create_all_tables` runs against a real PostgreSQL server in
`tests/integration/test_init_db.py`; these tests cover everything else
with fakes, so no database or Hydra config composition is needed.
"""

import logging
from types import SimpleNamespace

import pytest
from omegaconf import OmegaConf

from genreguru.db import init_db

MIN_PG_MAJOR = init_db.MIN_PG_MAJOR


class _FakeConn:
    """A `connect()` context manager whose `execute` is safe to call."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, stmt):
        return self


class _FakeEngine:
    def __init__(self, dialect=None):
        self.dialect = dialect or SimpleNamespace(server_version_info=(MIN_PG_MAJOR, 8))
        self.disposed = False

    def connect(self):
        return _FakeConn()

    def dispose(self):
        self.disposed = True


class _FakeLoggingManager:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def setup(self, log_cfg):
        pass


def test_dry_run_ddl_gen_logs_every_table(caplog):
    """Test DDL is logged for every table without touching a database."""
    with caplog.at_level(logging.INFO, logger="genreguru.db.init_db"):
        init_db.dry_run_ddl_gen()

    messages = " ".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "genreguru.db.init_db"
    )
    assert all(
        (
            "dry-run mode: logging generated DDL only" in messages,
            "CREATE TABLE songs" in messages,
            "CREATE TABLE song_fingerprints" in messages,
            "CREATE TABLE song_artists" in messages,
        )
    )


def test_health_check_successful_connection():
    """Test `health_check` accepts a reachable engine without raising."""
    init_db.health_check(_FakeEngine())  # ty: ignore[invalid-argument-type]


def test_health_check_failure_reraises(caplog):
    """Test a failed connection logs an exception and re-raises."""

    class _FailingEngine:
        def connect(self):
            raise ConnectionError("db down")

    with pytest.raises(ConnectionError):
        init_db.health_check(_FailingEngine())  # ty: ignore[invalid-argument-type]
    assert "engine health-check failed" in caplog.text


def test_verify_pg_version_accepts_supported():
    """Test `verify_pg_version` passes on the minimum supported server."""
    init_db.verify_pg_version(_FakeEngine())  # ty: ignore[invalid-argument-type]


def test_verify_pg_version_rejects_old_server(caplog):
    """Test an unsupported major raises RuntimeError and logs an error."""
    old = _FakeEngine(dialect=SimpleNamespace(server_version_info=(17, 9)))
    with pytest.raises(RuntimeError, match="PostgreSQL 17 detected"):
        init_db.verify_pg_version(old)  # ty: ignore[invalid-argument-type]
    assert "unsupported postgres major version 17" in caplog.text


def test_main_dry_run_skips_engine(monkeypatch):
    """Test dry-run mode logs DDL and returns before building an engine."""
    cfg = OmegaConf.create({"db": {"dry_run": True}, "logging": {}})
    calls = []
    monkeypatch.setattr(init_db, "LoggingManager", _FakeLoggingManager)
    monkeypatch.setattr(init_db, "dry_run_ddl_gen", lambda: calls.append("dry_run"))
    monkeypatch.setattr(init_db, "create_engine", lambda cfg: calls.append("engine"))

    init_db.main(cfg)

    assert calls == ["dry_run"]


def test_main_success_disposes_engine(monkeypatch):
    """Test the full workflow runs in order and disposes the engine."""
    cfg = OmegaConf.create(
        {
            "db": {"dry_run": False, "url": "postgresql://u:p@localhost/db"},
            "logging": {},
        }
    )
    engine = _FakeEngine()
    calls = []
    monkeypatch.setattr(init_db, "LoggingManager", _FakeLoggingManager)
    monkeypatch.setattr(init_db, "create_engine", lambda cfg: engine)
    monkeypatch.setattr(init_db, "health_check", lambda eng: calls.append("health"))
    monkeypatch.setattr(
        init_db, "verify_pg_version", lambda eng: calls.append("verify")
    )
    monkeypatch.setattr(
        init_db, "create_all_tables", lambda eng: calls.append("create_all")
    )

    init_db.main(cfg)

    assert calls == ["health", "verify", "create_all"]
    assert engine.disposed is True


def test_main_failure_exits_one(monkeypatch, caplog):
    """Test a workflow failure disposes the engine and exits with code 1."""
    cfg = OmegaConf.create({"db": {"dry_run": False}, "logging": {}})
    engine = _FakeEngine()
    monkeypatch.setattr(init_db, "LoggingManager", _FakeLoggingManager)
    monkeypatch.setattr(init_db, "create_engine", lambda cfg: engine)

    def _boom(eng):
        raise RuntimeError("boom")

    monkeypatch.setattr(init_db, "health_check", _boom)

    with pytest.raises(SystemExit) as exc_info:
        init_db.main(cfg)

    assert exc_info.value.code == 1
    assert engine.disposed is True
    assert "Error encountered during table creation" in caplog.text
