"""SQLAlchemy declarative base for the GenreGuru core library."""

__all__ = [
    "Base",
    "TimestampedMixin",
    "UuidMixin",
]

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_constraint_naming_conventions = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all `genreguru` ORM models.

    Provides:
    - Consistent naming conventions for constraints (ix, uq, fk, pk).
    - Opt-in mixins: `TimestampedMixin` and `UuidMixin`.
    """

    metadata = MetaData(naming_convention=_constraint_naming_conventions)


class TimestampedMixin:
    """Mixin that adds `created_at` / `updated_at` audit columns.

    Models that inherit this will automatically get:
    - `created_at`: server_default=func.now() on insert.
    - `updated_at`: server_default=func.now() on insert & update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UuidMixin:
    """Mixin that provides a UUID primary key.

    Sets `id` to a UUID column with server-side `uuidv7()`. Models
    that use this mixin should NOT define their own `id` column.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuidv7()
    )
