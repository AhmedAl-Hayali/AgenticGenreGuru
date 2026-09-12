"""Unit tests for `genreguru.gglogging` lifecycle, ownership, and handler components."""

import io
import json
import logging
from typing import Any

import pytest
from omegaconf import OmegaConf

from genreguru import gglogging
from genreguru.gglogging import (
    FingerprintContextAdapter,
    JsonFormatter,
    LoggingManager,
    NonErrorFilter,
    RichStreamHandler,
    SafeRotatingFileHandler,
    log_fingerprint_outcome,
    timer,
)

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


def test_install_queue_handler_idempotent(log_cfg):
    """Test a second install leaves the named fan-out untouched."""
    manager = LoggingManager()
    manager.setup(log_cfg)
    first_listener = manager._listener
    manager._install_queue_handler()
    assert _root_handler_names() == [_QUEUE_HANDLER_NAME]
    assert manager._listener is first_listener


def test_rollback_install_with_active_fanout(log_cfg):
    """Test rollback when a listener and handler are already attached."""
    manager = LoggingManager()
    manager.setup(log_cfg)
    manager._rollback_install([])
    assert manager._listener is None
    assert manager._handler is None
    assert _root_handler_names() == []


def _make_record(
    level: int = logging.INFO,
    msg: str = "hello",
    args=None,
    **attrs,
) -> logging.LogRecord:
    """A throwaway `LogRecord`, optionally carrying context *attrs*."""
    record = logging.LogRecord(
        name="genreguru.test",
        level=level,
        pathname=__file__,
        lineno=42,
        msg=msg,
        args=args,
        exc_info=None,
    )
    for key, value in attrs.items():
        setattr(record, key, value)
    return record


def _capture_records(
    target: logging.Logger,
) -> tuple[logging.Handler, list[Any]]:
    """Attach a capturing handler to *target*, returning `(handler, sink)`.

    Records carry `extra`-injected context attributes that do not exist on
    `logging.LogRecord`, so the sink is typed `Any`.
    """

    class _Capture(logging.Handler):
        def __init__(self, sink: list[Any]) -> None:
            super().__init__(level=logging.DEBUG)
            self.sink = sink

        def emit(self, record: logging.LogRecord) -> None:
            self.sink.append(record)

    sink: list[Any] = []
    handler = _Capture(sink)
    target.addHandler(handler)
    return handler, sink


class TestJsonFormatter:
    """Pin the JSONL rendering of `JsonFormatter`."""

    @staticmethod
    def _render(**attrs) -> dict:
        return json.loads(JsonFormatter().format(_make_record(**attrs)))

    def test_default_fields_present(self):
        """Every default field must be emitted (message rendered via args)."""
        data = self._render(msg="hello %s", args=("world",))
        for key in (
            "level",
            "message",
            "timestamp",
            "logger",
            "module",
            "function",
            "line",
            "thread_name",
        ):
            assert key in data
        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert data["logger"] == "genreguru.test"

    def test_exc_info_wedge(self):
        """A record carrying exc_info must render it under `exc_info`."""
        record = _make_record()
        try:
            raise ValueError("boom")
        except ValueError as exc:
            record.exc_info = (type(exc), exc, exc.__traceback__)
        data = json.loads(JsonFormatter().format(record))
        assert "exc_info" in data

    def test_custom_fmt_keys_bind_json_field_to_attr(self):
        """`fmt_keys` remaps JSON field names to record attributes."""
        fmt = JsonFormatter(fmt_keys={"custom": "isrc"})
        data = json.loads(fmt.format(_make_record(isrc="GBDUW0000059")))
        assert data["custom"] == "GBDUW0000059"
        assert "isrc" not in data
        assert "deezer_id" not in data


class TestNonErrorFilter:
    """Pin `NonErrorFilter`: only sub-ERROR levels pass."""

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (logging.INFO, True),
            (logging.ERROR, False),
        ],
        ids=["sub_error_passes", "error_blocked"],
    )
    def test_level_gate(self, level, expected):
        """Sub-ERROR levels pass; ERROR and above are blocked."""
        assert NonErrorFilter().filter(_make_record(level=level)) is expected


class TestSafeRotatingFileHandler:
    """Pin `SafeRotatingFileHandler` parent-directory creation."""

    def test_creates_parent_directory_on_emit(self, tmp_path):
        """A nested path with no existing parent must work without setup."""
        target = tmp_path / "nested" / "logs" / "app.log"
        handler = SafeRotatingFileHandler(str(target))
        try:
            handler.emit(_make_record(msg="hi"))
            assert target.is_file()
            assert target.read_text() == "hi\n"
        finally:
            handler.close()


class TestRichStreamHandler:
    """Pin `RichStreamHandler` explicit-stream binding."""

    def test_console_writes_to_provided_stream(self):
        """The Rich console must be bound to the caller-supplied stream."""
        stream = io.StringIO()
        handler = RichStreamHandler(stream=stream)
        assert handler.console.file is stream


class TestFingerprintContextAdapterProcess:
    """Pin `FingerprintContextAdapter.process` extra-merging."""

    def test_caller_extra_not_clobbered(self):
        """A caller-supplied `extra` must merge with, not replace, the context."""
        adapter = FingerprintContextAdapter(
            logging.getLogger("genreguru.test"), {"isrc": "GBDUW0000059"}
        )
        _msg, kwargs = adapter.process("hello", {"extra": {"song_id": "s1"}})
        assert kwargs["extra"] == {"song_id": "s1", "isrc": "GBDUW0000059"}


class TestLogFingerprintOutcome:
    """Pin `log_fingerprint_outcome` INFO records and their context extras."""

    @staticmethod
    def _emit(reused: bool) -> list[Any]:
        target = logging.getLogger("genreguru.fingerprint_service.test")
        target.setLevel(logging.DEBUG)
        handler, sink = _capture_records(target)
        try:
            log_fingerprint_outcome(
                isrc="GBDUW0000059",
                deezer_id=3135556,
                song_id="s1",
                reused=reused,
                elapsed=1.5,
                target=target,
            )
        finally:
            target.removeHandler(handler)
        return sink

    def test_fresh_message_and_context(self):
        """A fresh fingerprint must log an INFO record with the full context."""
        (record,) = self._emit(reused=False)
        assert record.levelno == logging.INFO
        assert record.getMessage() == (
            "fresh fingerprint generated (isrc=GBDUW0000059 elapsed=1.50s song_id=s1)"
        )
        assert record.isrc == "GBDUW0000059"
        assert record.deezer_id == 3135556
        assert record.song_id == "s1"
        assert record.reused is False

    def test_reused_message_and_context(self):
        """A reused fingerprint must log an INFO record with the full context."""
        (record,) = self._emit(reused=True)
        assert record.levelno == logging.INFO
        assert (
            record.getMessage() == "fingerprint reused (isrc=GBDUW0000059 song_id=s1)"
        )
        assert record.reused is True
        assert record.isrc == "GBDUW0000059"


class TestTimer:
    """Pin the monotonic `timer` context manager."""

    def test_elapsed_is_non_negative_and_monotonic(self):
        """`elapsed()` must report a growing non-negative float."""
        with timer() as elapsed:
            first = elapsed()
            assert first >= 0
            assert elapsed() >= first
