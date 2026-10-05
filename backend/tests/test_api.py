from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.deps import require_role
from app.auth.session import COOKIE
from app.db.base import SessionLocal
from app.db.models import User


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok"}


def test_me_needs_sign_in(client: TestClient) -> None:
    r = client.get("/api/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "Please sign in."


def test_dev_sign_in_flow(client: TestClient) -> None:
    options = client.get("/api/auth/options").json()
    assert options["provider"] == "dev"
    emails = {u["email"] for u in options["users"]}
    assert {"rahulgupta@cityholdings.com.mm", "owner@dev.local"} <= emails

    r = client.post("/api/auth/login", json={"email": "Owner@dev.local "})
    assert r.status_code == 200
    assert r.json()["role"] == "owner"
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie

    assert client.get("/api/me").json()["email"] == "owner@dev.local"
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/me").status_code == 401


def test_unknown_user_cannot_sign_in(client: TestClient) -> None:
    assert client.post("/api/auth/login", json={"email": "nobody@x"}).status_code == 401
    assert client.post("/api/auth/login", json={}).status_code == 401


def test_tampered_cookie_is_ignored(client: TestClient) -> None:
    client.post("/api/auth/login", json={"email": "owner@dev.local"})
    token = client.cookies.get(COOKIE)
    client.cookies.set(COOKIE, token[:-2] + "xx")
    assert client.get("/api/me").status_code == 401


def test_require_role(client: TestClient) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]

    @app.get("/api/_test/admin-only")
    def admin_only(_=Depends(require_role("admin"))) -> dict:
        return {"ok": True}

    # The catch-all /api route was added first, so move the test route ahead of it.
    app.router.routes.insert(0, app.router.routes.pop())

    assert client.get("/api/_test/admin-only").status_code == 401
    client.post("/api/auth/login", json={"email": "owner@dev.local"})
    assert client.get("/api/_test/admin-only").status_code == 403
    client.post("/api/auth/login", json={"email": "rahulgupta@cityholdings.com.mm"})
    assert client.get("/api/_test/admin-only").json() == {"ok": True}


def test_require_role_rejects_unknown_role() -> None:
    with pytest.raises(ValueError):
        require_role("superuser")


def test_screens_are_served(client: TestClient) -> None:
    assert "City Prism" in client.get("/").text
    assert "City Prism" in client.get("/projects/abc").text  # app shell fallback
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/api/nothing-here").status_code == 404
    assert client.get("/../../etc/passwd").status_code in (200, 404)
    assert "root:" not in client.get("/..%2F..%2Fetc%2Fpasswd").text


def test_prod_needs_secret_and_has_no_dev_sign_in(
    settings_env, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import Settings, get_settings

    monkeypatch.setenv("ENV", "prod")
    with pytest.raises(ValueError):
        Settings()
    monkeypatch.setenv("SECRET_KEY", "a-real-secret")
    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as c:
        assert c.get("/api/auth/options").json() == {"provider": "none", "users": []}
        assert c.post("/api/auth/login", json={"email": "owner@dev.local"}).status_code == 401
        assert c.get("/api/docs").status_code == 404
    with SessionLocal() as db:  # dev test users are never seeded in production
        assert db.scalars(select(User.email)).all() == ["rahulgupta@cityholdings.com.mm"]
