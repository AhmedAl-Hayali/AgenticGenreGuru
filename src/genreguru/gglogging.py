"""Configure centralized logging for `genreguru`.

Design authority: docs/001-song-fingerprint-engine/logging-report.md.
Consumes the Hydra `logging` config group via `genreguru.config`; no
hard-coded handler dict lives here.
"""

import json
import logging
import logging.config
import queue
from datetime import UTC, datetime
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from typing import Any, cast

from omegaconf import OmegaConf
from rich.console import Console
from rich.logging import RichHandler

from genreguru.config import get_config

logger = logging.getLogger(__name__)

_listener: QueueListener | None = None
_configured = False


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
    """Create a rotating JSONL handler that creates its parent directory on demand."""

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

    def __init__(self, stream: Any = None, **kwargs) -> None:
        """Initialize the handler with an explicit output stream.

        Args:
            stream: Output stream for the Rich console. If None, uses default.
            **kwargs: Keyword arguments passed to the parent RichHandler.
        """
        console = Console(file=stream) if stream is not None else None
        super().__init__(console=console, **kwargs)


def install_queue_handler() -> None:
    """Fan root handlers out behind a named QueueHandler + QueueListener."""
    global _listener
    root = logging.getLogger()
    if logging.getHandlerByName("queue_handler") is not None:
        return
    sink_queue: queue.Queue[Any] = queue.Queue()
    existing = list(root.handlers)
    handler = QueueHandler(sink_queue)
    handler.name = "queue_handler"
    root.handlers = [handler]
    _listener = QueueListener(sink_queue, *existing, respect_handler_level=True)
    _listener.start()


def setup_logging() -> None:
    """Build the `dictConfig` from the active Hydra `logging` group.

    Idempotent: subsequent calls are no-ops, preventing a second
    `QueueListener` thread from being spawned after a re-config.
    """
    global _configured
    if _configured:
        return
    cfg = get_config()
    log_cfg = cfg.logging
    config_dict = cast(dict[str, Any], OmegaConf.to_container(log_cfg, resolve=True))
    logging.config.dictConfig(config_dict)
    install_queue_handler()
    _configured = True


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
    """Emit the reused/fresh fingerprint INFO record through the adapter.

    Args:
        isrc: International Standard Recording Code.
        deezer_id: Deezer track ID.
        song_id: Internal song record UUID.
        reused: Whether the fingerprint was reused from an existing record.
        elapsed: Time in seconds for fingerprint generation (0 if reused).
        target: Logger to emit through. Defaults to fingerprint_service logger.
    """
    source = target or logging.getLogger("genreguru.fingerprint_service")
    adapter = FingerprintContextAdapter(
        source,
        {"isrc": isrc, "deezer_id": deezer_id, "song_id": song_id, "reused": reused},
    )
    if reused:
        adapter.info("fingerprint reused (isrc=%s song_id=%s)", isrc, song_id)
    else:
        adapter.info(
            "fresh fingerprint generated (isrc=%s elapsed=%.2fs song_id=%s)",
            isrc,
            elapsed,
            song_id,
        )
