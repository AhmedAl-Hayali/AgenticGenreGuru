"""Unit tests for `genreguru.gglogging` lifecycle and ownership semantics."""

import logging

import pytest
from omegaconf import OmegaConf

from genreguru import gglogging
from genreguru.gglogging import LoggingManager

_QUEUE_HANDLER_NAME = gglogging._QUEUE_HANDLER_NAME


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Tear down any owner and clear root handlers before and after each test."""

    def _reset() -> None:
        if gglogging._owner is not None:
            gglogging._owner.teardown()
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)

    _reset()
    yield
    _reset()


@pytest.fixture
def log_cfg(tmp_path):
    """Build a minimal logging config writing to a temp file."""
    return OmegaConf.create(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"f": {"format": "%(message)s"}},
            "handlers": {
                "fh": {
                    "class": "logging.FileHandler",
                    "filename": str(tmp_path / "smoke.log"),
                    "formatter": "f",
                }
            },
            "root": {"level": "INFO", "handlers": ["fh"]},
        }
    )


def _root_handler_names() -> list[str | None]:
    return [h.name for h in logging.getLogger().handlers]


def test_nested_context_managers(log_cfg):
    """Test inner managers defer and their exit does not release the outer.

    Covers the deferred-manager invariant (inner setup installs nothing) and
    the non-owner-teardown invariant (inner exit leaves the owner's fan-out
    intact) in one dialog.
    """
    m1 = LoggingManager()
    m2 = LoggingManager()
    with m1:
        m1.setup(log_cfg)
        assert gglogging._owner is m1
        assert m1._listener is not None
        with m2:
            m2.setup(log_cfg)
            assert gglogging._owner is m1
            assert m2._listener is None and m2._handler is None
        assert gglogging._owner is m1
        assert m1._listener is not None
    assert gglogging._owner is None and _root_handler_names() == []


def test_rollback_on_failure(tmp_path):
    """Test a failed setup restores prior handlers and releases ownership."""
    bad_conf = OmegaConf.create(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "badHandler": {
                    "class": "logging.NonExistentHandlerClass",
                    "filename": str(tmp_path / "bad.log"),
                }
            },
            "root": {"level": "INFO", "handlers": ["badHandler"]},
        }
    )
    manager = LoggingManager()
    before = list(logging.getLogger().handlers)
    with pytest.raises(ValueError):
        manager.setup(bad_conf)
    assert gglogging._owner is None
    assert logging.getLogger().handlers == before
    assert manager._listener is None and manager._handler is None


def test_manager_contextmanager(log_cfg):
    """Test the manager's own context manager claims and releases."""
    with LoggingManager() as manager:
        manager.setup(log_cfg)
        assert gglogging._owner is manager
    assert gglogging._owner is None and _root_handler_names() == []
