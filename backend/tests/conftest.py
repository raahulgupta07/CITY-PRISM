from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import SessionLocal, reset_engine


@pytest.fixture
def settings_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh SQLite file and a tiny fake build folder for each test."""
    build = tmp_path / "build"
    build.mkdir()
    (build / "index.html").write_text("<!doctype html><title>City Prism</title>")
    (build / "favicon.svg").write_text("<svg/>")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("FRONTEND_BUILD_DIR", str(build))
    get_settings.cache_clear()
    reset_engine()
    yield tmp_path
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client(settings_env: Path) -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as c:  # runs migrations and the seed
        yield c


@pytest.fixture
def db(client: TestClient) -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
