"""Runtime initialization for the GenreGuru web application.

`settings/` modules are side-effect free (see `settings/base.py`); this
module owns the process-level runtime setup that used to live there —
logging configuration and the shared SQLAlchemy engine. Entrypoints
(`manage.py`, `wsgi.py`, `asgi.py`) call `init_runtime()` once before
serving. Tests build their own engine fixtures (see `tests/conftest.py`)
and never invoke this.
"""

from genreguru.config import get_config
from genreguru.db.engine import create_engine
from genreguru.gglogging import LoggingManager

_initialized = False


def init_runtime() -> None:
    """Configure logging and create the shared engine exactly once.

    Idempotent: repeated calls (e.g. manage.py forks or test bootstrap)
    are no-ops after the first. Safe to call before `django.setup()`.
    """
    global _initialized
    if _initialized:
        return
    cfg = get_config()
    LoggingManager().setup(cfg.logging)
    create_engine(cfg.db)
    _initialized = True
