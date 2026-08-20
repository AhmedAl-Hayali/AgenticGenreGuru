"""Configure centralized logging for `genreguru`.

Design authority: docs/001-song-fingerprint-engine/logging-report.md.
Callers pass in the logging config (from Hydra or otherwise); this module
owns `dictConfig`, the queue handler, and lifecycle — no config
composition happens here.

Public API::

    # Long-lived process (Django boot, standalone CLI)
    manager = LoggingManager()
    manager.setup(log_cfg)

    # Short-lived scripts / test fixtures (teardown automatic on exit)
    with LoggingManager() as manager:
        manager.setup(log_cfg)
        ...

    # Full control (tests, serialized lifecycle)
    manager = LoggingManager()
    manager.setup(log_cfg)
    ...
    manager.teardown()
"""

import json
import logging
import logging.config
import queue
from datetime import UTC, datetime
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import IO, Any, cast

from omegaconf import DictConfig, OmegaConf
from rich.console import Console
from rich.logging import RichHandler

_QUEUE_HANDLER_NAME = "queue_handler"
_owner: LoggingManager | None = None
_owner_lock = Lock()


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON line (JSONL)."""

    _DEFAULT_FMT_KEYS = {
        "isrc": "isrc",
        "deezer_id": "deezer_id",
        "song_id": "song_id",
        "reused": "reused",
    }

    def __init__(self, fmt_keys: dict | None = None, *args, **kwargs) -> None:
        """Initialize the formatter.

        Args:
            fmt_keys: Mapping of JSON field names to log record attributes.
                Defaults to tracking isrc, deezer_id, song_id, and reused.
            *args: Positional arguments passed to the parent Formatter.
            **kwargs: Keyword arguments passed to the parent Formatter.
        """
        super().__init__(*args, **kwargs)
        self.fmt_keys = fmt_keys if fmt_keys is not None else self._DEFAULT_FMT_KEYS

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as a single JSON line.

        Args:
            record: The log record to format.

        Returns:
            A JSON string containing the formatted log entry.
        """
        record.message = record.getMessage()
        data = {
            "level": record.levelname,
            "message": record.message,
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread_name": record.threadName,
        }
        for json_field, attr in self.fmt_keys.items():
            value = getattr(record, attr, None)
            if value is not None:
                data[json_field] = value
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


class NonErrorFilter(logging.Filter):
    """Pass only records below ERROR (DEBUG/INFO/WARNING)."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Check if the record is below ERROR level.

        Args:
            record: The log record to evaluate.

        Returns:
            True if the record level is below ERROR, False otherwise.
        """
        return record.levelno < logging.ERROR


class SafeRotatingFileHandler(RotatingFileHandler):
    """Create a rotating log handler that creates its parent directory on demand."""

    def __init__(self, filename: str | Path, *args, **kwargs) -> None:
        """Initialize the handler, creating the parent directory if needed.

        Args:
            filename: Path to the log file.
            *args: Positional arguments passed to the parent RotatingFileHandler.
            **kwargs: Keyword arguments passed to the parent RotatingFileHandler.
        """
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, *args, **kwargs)


class RichStreamHandler(RichHandler):
    """Bind a RichHandler to an explicit stream (stdout/stderr)."""

    def __init__(self, stream: IO | None = None, **kwargs) -> None:
        """Initialize the handler with an explicit output stream.

        Args:
            stream: Output stream for the Rich console. If None, uses default.
            **kwargs: Keyword arguments passed to the parent RichHandler.
        """
        console = Console(file=stream) if stream is not None else None
        super().__init__(console=console, **kwargs)


class LoggingManager:
    """Own the `QueueListener` lifecycle and root-handler fan-out.

    One active manager per process — `logging` root state is global, so
    instances are serialized owners; late starters defer and `teardown()`
    removes only this instance's handler. Takes no constructor args; a
    fresh instance activates on its first `setup()` call. Application
    code uses `logging.getLogger` directly.
    """

    def __init__(self) -> None:
        self._listener: QueueListener | None = None
        self._handler: QueueHandler | None = None

    def setup(self, log_cfg: dict | DictConfig) -> None:
        """Claim the process root; no-op if a manager already owns it.

        Args:
            log_cfg: Logging config dict or OmegaConf DictConfig (e.g. the
                `logging` group from the Hydra config tree).  Resolved and
                converted to a plain dict internally.

        Ownership is claimed under `_owner_lock`; the winner installs the
        queue fan-out, losers return silently. On install failure the root
        is rolled back to its prior handlers and ownership is released.
        """
        global _owner
        with _owner_lock:
            if _owner is not None:
                return
            _owner = self
            snapshot = list(logging.getLogger().handlers)
            try:
                config_dict = cast(
                    dict[str, Any], OmegaConf.to_container(log_cfg, resolve=True)
                )
                logging.config.dictConfig(config_dict)
                self._install_queue_handler()
            except BaseException:
                self._rollback_install(snapshot)
                _owner = None
                raise

    def _install_queue_handler(self) -> None:
        """Fan root handlers out behind a named QueueHandler + QueueListener."""
        root = logging.getLogger()
        if logging.getHandlerByName(_QUEUE_HANDLER_NAME) is not None:
            return
        sink_queue: queue.Queue[Any] = queue.Queue()
        existing = list(root.handlers)
        handler = QueueHandler(sink_queue)
        handler.name = _QUEUE_HANDLER_NAME
        root.handlers = [handler]
        self._handler = handler
        self._listener = QueueListener(
            sink_queue, *existing, respect_handler_level=True
        )
        self._listener.start()

    def _rollback_install(self, snapshot: list[logging.Handler]) -> None:
        """Undo a partial install, restoring the previous root handlers."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
            self._handler = None
        logging.getLogger().handlers = snapshot

    def teardown(self) -> None:
        """Release the root only if this instance owns it.

        Safe to call multiple times or on a manager that never claimed
        ownership. After teardown the root logger has **no handlers**; any
        log emission before the next `setup()` call is silently dropped.
        This is intentional — callers that need continuous logging should
        not tear down (e.g. long-running Django processes).
        """
        global _owner
        with _owner_lock:
            if _owner is not self:
                return
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
            if self._handler is not None:
                logging.getLogger().removeHandler(self._handler)
                self._handler = None
            _owner = None

    def __enter__(self) -> LoggingManager:
        """Enter the context manager.

        Returns:
            This manager instance, ready for `setup()` calls.
        """
        return self

    def __exit__(self, *_: Any) -> None:
        """Exit the context manager, releasing ownership via `teardown()`."""
        self.teardown()


class FingerprintContextAdapter(logging.LoggerAdapter):
    """Inject isrc/deezer_id/song_id/reused context via `extra`."""

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:  # ty: ignore[invalid-method-override]
        """Inject context fields into the log record extra dict.

        Args:
            msg: The log message.
            kwargs: Keyword arguments including optional extra dict.

        Returns:
            Tuple of (message, kwargs) with extra fields merged.
        """
        kwargs.setdefault("extra", {}).update(self.extra)
        return msg, kwargs


def log_fingerprint_outcome(
    isrc: str,
    deezer_id: int,
    song_id: str,
    reused: bool,
    elapsed: float,
    target: logging.Logger | None = None,
) -> None:
    """Emit the reused/fresh fingerprint INFO record with context fields.

    Args:
        isrc: International Standard Recording Code.
        deezer_id: Deezer track ID.
        song_id: Internal song record UUID.
        reused: Whether the fingerprint was reused from an existing record.
        elapsed: Time in seconds for fingerprint generation (0 if reused).
        target: Logger to emit through. Defaults to fingerprint_service logger.
    """
    source = target or logging.getLogger("genreguru.fingerprint_service")
    extra = {
        "isrc": isrc,
        "deezer_id": deezer_id,
        "song_id": song_id,
        "reused": reused,
    }
    if reused:
        source.info(
            "fingerprint reused (isrc=%s song_id=%s)", isrc, song_id, extra=extra
        )
    else:
        source.info(
            "fresh fingerprint generated (isrc=%s elapsed=%.2fs song_id=%s)",
            isrc,
            elapsed,
            song_id,
            extra=extra,
        )
