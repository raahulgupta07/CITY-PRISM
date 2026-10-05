from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, login


def test_only_admin(client: TestClient) -> None:
    for email in ("owner@dev.local", "reviewer@dev.local", "approver@dev.local"):
        login(client, email)
        assert client.get("/api/admin/users").status_code == 403
        assert client.put("/api/admin/questions/1.1", json={"text": "New text?"}).status_code == 403


def test_edit_question_makes_new_version(client: TestClient) -> None:
    login(client, ADMIN_EMAIL)
    r = client.put("/api/admin/questions/1.1", json={"text": " Is the problem clear? "})
    assert r.json()["text"] == "Is the problem clear?" and r.json()["version"] == 2
    r = client.put("/api/admin/questions/1.1", json={"text": "Is the problem clear?"})
    assert r.json()["version"] == 2  # same text, same version
    r = client.put("/api/admin/questions/1.1", json={"is_draft": False})
    assert r.json()["is_draft"] is False and r.json()["version"] == 2
    q = client.get("/api/questions").json()[0]["questions"][0]
    assert q["text"] == "Is the problem clear?" and not q["is_draft"]
    assert client.put("/api/admin/questions/1.1", json={"text": "ab"}).status_code == 422
    assert client.put("/api/admin/questions/9.1", json={"text": "Valid text"}).status_code == 404

    r = client.put("/api/admin/dimensions/1", json={"lead_question": "Is this the right one?"})
    assert r.json()["lead_question"] == "Is this the right one?"


def test_users_and_roles(client: TestClient) -> None:
    admin = login(client, ADMIN_EMAIL)
    r = client.post("/api/admin/users", json={"name": "Ma Swe", "email": "MaSwe@city.mm"})
    assert r.status_code == 201 and r.json()["email"] == "maswe@city.mm"
    assert r.json()["role"] == "owner"
    uid = r.json()["id"]
    assert (
        client.post("/api/admin/users", json={"name": "x", "email": "maswe@city.mm"}).status_code
        == 409
    )
    assert client.post("/api/admin/users", json={"name": "x", "email": "bad"}).status_code == 422

    assert client.patch(f"/api/admin/users/{uid}", json={"role": "reviewer"}).json()["role"] == (
        "reviewer"
    )
    assert client.patch(f"/api/admin/users/{uid}", json={"role": "boss"}).status_code == 422
    # The last admin cannot lose the role.
    r = client.patch(f"/api/admin/users/{admin['id']}", json={"role": "owner"})
    assert r.status_code == 409
    client.patch(f"/api/admin/users/{uid}", json={"role": "admin"})
    r = client.patch(f"/api/admin/users/{admin['id']}", json={"role": "reviewer"})
    assert r.json()["role"] == "reviewer"
