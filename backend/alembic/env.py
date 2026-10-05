from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from app.db import models  # noqa: F401  (registers the tables)
from app.db.base import Base, get_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(get_engine().url),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is None:
        with get_engine().connect() as connection:
            _run(connection)
    else:
        _run(connection)


def _run(connection) -> None:  # noqa: ANN001
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
