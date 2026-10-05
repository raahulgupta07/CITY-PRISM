"""Run Alembic migrations from code (the app does this on start)."""

from __future__ import annotations

from alembic.config import Config

from alembic import command
from app.config import BACKEND_DIR
from app.db.base import get_engine


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade_to_head() -> None:
    cfg = alembic_config()
    with get_engine().begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
