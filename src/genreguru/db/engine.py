"""Database engine + session factory for the GenreGuru core library.

Reads connection config from the Hydra `db` group via
`genreguru/config.py`; the URL string is resolved from the composed config
and may carry `${oc.env:...}` secrets.

Programmatic URL generation is preferred: individual components (`dialect`,
`driver`, `user`, `password`, `host`, `port`, `database`) are resolved from
env vars with sensible defaults in `dev`.

Logging contract (docs/001-song-fingerprint-engine/logging-report.md §T007):
- INFO once on engine init: host, database name, pool size, dialect —
  never the password.
- DEBUG on pool connect/checkout/checkin events (DBAPI connection
  lifecycle, attached to the engine — not to sessions).
- WARNING on pool invalidate (connection lost).
"""

__all__ = [
    "SessionLocal",
    "get_session_factory",
    "create_engine",
    "make_session_factory",
    "make_scoped_session",
]

import logging

from omegaconf import DictConfig
from omegaconf.errors import ConfigAttributeError
from psycopg import Connection
from sqlalchemy import URL, event
from sqlalchemy import create_engine as _sa_create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

logger = logging.getLogger(__name__)

SessionLocal: sessionmaker[Session] = sessionmaker()
"""Default session factory; rebound by `create_engine`.

Access as a module attribute (`genreguru.db.engine.SessionLocal`) or via
`get_session_factory()`. A direct `from genreguru.db.engine import
SessionLocal` executed before `create_engine()` captures the unbound
factory and never sees the rebind.
"""


def get_session_factory() -> sessionmaker[Session]:
    """Return the current default session factory (post-`create_engine`)."""
    return SessionLocal


def _build_url(db_cfg: DictConfig) -> URL:
    """Build a SQLAlchemy URL from individual db config components.

    Each component is resolved from environment variables with sensible defaults.

    Args:
        db_cfg: The `db` group of the composed config.

    Returns:
        A `URL` instance representing the connection URL.

    Raises:
        omegaconf.errors.ConfigAttributeError: If any required db config
            attribute is missing.
    """
    try:
        dialect = str(db_cfg.dialect)  # e.g. "postgresql"
        driver = str(db_cfg.driver)  # e.g. "psycopg"
        user = str(db_cfg.user)
        password = str(db_cfg.password)
        host = str(db_cfg.host)
        port = int(db_cfg.port)
        database = str(db_cfg.database)
    except ConfigAttributeError as e:
        logger.error("Missing db config attribute: %s", e)
        raise

    url = URL.create(
        drivername=f"{dialect}+{driver}",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )
    return url


def create_engine(db_cfg: DictConfig, **engine_kwargs) -> Engine:
    """Create a SQLAlchemy engine from the composed Hydra `db` group.

    Individual components (`dialect`, `driver`, `user`, `password`, `host`,
    `port`, `database`, `pool_size`, `max_overflow`, `echo`) are resolved from
    env vars with sensible defaults (see config/db/*.yaml). Rebinds the module-level
    `SessionLocal` to the new engine.

    Args:
        db_cfg: The `db` group of the composed config (e.g. `cfg.db` from
            `genreguru.config.get_config()`).
        **engine_kwargs: Extra kwargs forwarded verbatim to
            `sqlalchemy.create_engine` (e.g. `connect_args`).

    Returns:
        A configured SQLAlchemy engine backed by the configured driver.

    Raises:
        omegaconf.errors.InterpolationResolutionError: If any required
            env var, e.g. `${oc.env:DB_USER}`, is unset.
    """
    url = _build_url(db_cfg)
    engine = _sa_create_engine(
        url,
        pool_size=int(db_cfg.pool_size),
        max_overflow=int(db_cfg.max_overflow),
        echo=bool(db_cfg.echo),
        pool_pre_ping=True,
        **engine_kwargs,
    )
    logger.info(
        "engine initialized host=%s database=%s pool_size=%d max_overflow=%d dialect=%s",
        url.host,
        url.database,
        int(db_cfg.pool_size),
        int(db_cfg.max_overflow),
        url.get_backend_name(),
    )
    _attach_pool_events(engine)
    global SessionLocal
    SessionLocal = make_session_factory(engine)
    return engine


def _attach_pool_events(engine: Engine) -> None:
    """Attach pool event listeners: DEBUG on connect/checkout/checkin, WARNING on invalidate."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _connection_record) -> None:
        logger.debug("new dbapi connection (%s)", dbapi_connection.__class__.__name__)

    @event.listens_for(engine, "checkout")
    def _on_checkout(_dbapi_connection, _connection_record, _connection_proxy) -> None:
        logger.debug("connection checked out from pool")

    @event.listens_for(engine, "checkin")
    def _on_checkin(_dbapi_connection, _connection_record) -> None:
        logger.debug("connection returned to pool")

    @event.listens_for(engine.pool, "invalidate")
    def _on_invalidate(
        dbapi_connection: Connection, _connection_record, _exception
    ) -> None:
        try:
            host = dbapi_connection.info.host
        except AttributeError:
            host = "UNKNOWN_HOST"
        logger.warning("connection to database lost (host=%s)", host)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a sessionmaker bound to the given engine.

    Sessions do not expire instances on commit (`expire_on_commit=False`)
    and autoflush before queries.

    Args:
        engine: Engine produced by `create_engine`.

    Returns:
        A configured `sessionmaker` bound to the engine.
    """
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


def make_scoped_session() -> scoped_session[Session]:
    """Build an unbound scoped session with production-ready defaults.

    Returns a `scoped_session` whose underlying `sessionmaker` shares
    the same settings as `make_session_factory` (`expire_on_commit=False`,
    `autoflush=True`) but is not yet bound to an engine.  Call
    returned `scoped_session.configure(bind=engine)` before use.

    Returns:
        A `scoped_session` ready to be configured with an engine.
    """
    return scoped_session(sessionmaker(expire_on_commit=False, autoflush=True))
