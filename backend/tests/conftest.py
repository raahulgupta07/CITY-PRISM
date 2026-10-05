from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import httpx
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


ADMIN_EMAIL = "rahulgupta@cityholdings.com.mm"


def login(client: TestClient, email: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email})
    assert r.status_code == 200, r.text
    return r.json()


def project_id(client: TestClient, name: str) -> str:
    for p in client.get("/api/projects").json():
        if p["name"] == name:
            return p["id"]
    raise AssertionError(f"no project {name}")


class FakeOpenRouter:
    """Stands in for OpenRouter. Queue replies; inspect what was sent."""

    def __init__(self) -> None:
        self.replies: list[httpx.Response | Exception] = []
        self.requests: list[dict] = []

    def reply(self, content: object, *, status: int = 200, cost: float = 0.0001) -> None:
        text = content if isinstance(content, str) else json.dumps(content)
        body = {
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 30, "cost": cost},
        }
        self.replies.append(httpx.Response(status, json=body))

    def fail(self, exc: Exception) -> None:
        self.replies.append(exc)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(
            {
                "url": str(request.url),
                "headers": dict(request.headers),
                "json": json.loads(request.content),
            }
        )
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def last_prompt(self) -> str:
        return self.requests[-1]["json"]["messages"][0]["content"]


@pytest.fixture
def fake_llm(settings_env, monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeOpenRouter]:
    from app.llm import client as llm

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.test/api/v1")
    monkeypatch.setenv("LLM_MODEL_FAST", "fast-model")
    monkeypatch.setenv("LLM_MODEL_DEFAULT", "default-model")
    get_settings.cache_clear()
    fake = FakeOpenRouter()
    monkeypatch.setattr(llm, "transport", httpx.MockTransport(fake.handler))
    yield fake
