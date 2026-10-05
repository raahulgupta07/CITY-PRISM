"""The migrations must build exactly the tables in models.py."""

from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db.base import Base, get_engine


def test_models_match_migrations(client) -> None:  # client runs `upgrade head`
    with get_engine().connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_sqlite_uses_wal(client) -> None:
    with get_engine().connect() as conn:
        assert conn.exec_driver_sql("PRAGMA journal_mode").scalar() == "wal"
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
