from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Answer
from tests.conftest import ADMIN_EMAIL, login, project_id


def test_reading_needs_sign_in(client: TestClient) -> None:
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/questions").status_code == 401


def test_questions(client: TestClient) -> None:
    login(client, "approver@dev.local")
    dims = client.get("/api/questions").json()
    assert [d["id"] for d in dims] == list(range(1, 9))
    assert all(len(d["questions"]) == 5 for d in dims)
    assert dims[0]["questions"][0]["is_draft"] and not dims[2]["questions"][0]["is_draft"]
    assert [q["id"] for q in dims[4]["questions"]] == ["5.1", "5.2", "5.3", "5.4", "5.5"]


def test_portfolio_is_weakest_first(client: TestClient) -> None:
    login(client, "approver@dev.local")
    rows = client.get("/api/projects").json()
    assert len(rows) == 12
    verdicts = [r["score"]["verdict"] for r in rows]
    assert verdicts == ["fix"] * 2 + ["go"] * 6 + ["ready"] + ["not_assessed"] * 3
    assert {r["name"] for r in rows[:2]} == {"CFC Model", "Fresh Replenishment"}
    cfc = next(r for r in rows if r["name"] == "CFC Model")
    assert cfc["score"]["weakest"] == [3] and cfc["score"]["lowest"] == 1.0
    assert cfc["score"]["dimensions"][2]["answered"] == 1
    assert cfc["owner"]["name"] == "Rahul Gupta"
    assert not any(r["can_edit"] for r in rows)  # approvers only read


def test_filters(client: TestClient) -> None:
    login(client, ADMIN_EMAIL)
    get = lambda q: [r["name"] for r in client.get(f"/api/projects?{q}").json()]  # noqa: E731
    assert len(get("verdict=fix")) == 2
    assert len(get("verdict=fix&verdict=ready")) == 3
    assert set(get("bu=Distribution")) == {
        "Consumer Insights (City Agent Insights)",
        "RO & ED Digital Conversion",
        "Coverage Planning (MCP) Tool",
    }
    assert len(get("stage=Production")) == 4
    assert len(get("mode=plan")) == 0
    assert len(get("mine=true")) == 12  # the admin owns all seed projects
    login(client, "owner@dev.local")
    assert get("mine=true") == []


def test_owner_creates_and_answers_own_project(client: TestClient) -> None:
    me = login(client, "owner@dev.local")
    r = client.post("/api/projects", json={"name": "  Invoice Bot ", "business_unit": "Finance"})
    assert r.status_code == 201
    p = r.json()
    assert p["name"] == "Invoice Bot" and p["owner"]["id"] == me["id"] and p["can_edit"]
    assert p["mode"] == "plan" and p["due_date"] is None
    assert p["score"]["verdict"] == "not_assessed"

    r = client.put(f"/api/projects/{p['id']}/answers/3.1", json={"answer": "Yes", "evidence": "x"})
    assert r.status_code == 200
    body = r.json()
    assert body["changed"] and body["answer"]["source"] == "person"
    assert body["answer"]["updated_by"]["name"] == "Test Owner"
    assert body["score"]["verdict"] == "ready" and body["score"]["answered"] == 1

    r = client.put(f"/api/projects/{p['id']}/answers/3.2", json={"answer": "No"})
    assert r.json()["score"]["verdict"] == "go"  # Yes + No = 3.0

    # Same values again: nothing changes, no new history row.
    r = client.put(f"/api/projects/{p['id']}/answers/3.2", json={"answer": "No"})
    assert r.json()["changed"] is False

    # Clear an answer (click the selected button again).
    r = client.put(f"/api/projects/{p['id']}/answers/3.2", json={"answer": None})
    assert r.json()["score"]["verdict"] == "ready"

    hist = client.get(f"/api/projects/{p['id']}/history").json()
    assert [(h["question_id"], h["old_answer"], h["new_answer"]) for h in hist] == [
        ("3.2", "No", None),
        ("3.2", None, "No"),
        ("3.1", None, "Yes"),
    ]
    assert (
        client.get(f"/api/projects/{p['id']}/history?question_id=3.1").json()[0]["changed_by"][
            "name"
        ]
        == "Test Owner"
    )


def test_assess_projects_default_due_date(client: TestClient) -> None:
    login(client, "reviewer@dev.local")
    p = client.post("/api/projects", json={"name": "Old bot", "mode": "assess"}).json()
    assert p["due_date"] == "2026-10-30"


def test_owner_cannot_edit_someone_elses_project(client: TestClient) -> None:
    login(client, "owner@dev.local")
    pid = project_id(client, "CFC Model")
    r = client.put(f"/api/projects/{pid}/answers/1.2", json={"answer": "Yes"})
    assert r.status_code == 403
    assert client.patch(f"/api/projects/{pid}", json={"stage": "Pilot / UAT"}).status_code == 403


def test_reviewer_edits_any_project_approver_none(client: TestClient) -> None:
    login(client, "reviewer@dev.local")
    pid = project_id(client, "CFC Model")
    assert client.put(f"/api/projects/{pid}/answers/1.2", json={"answer": "Yes"}).status_code == 200
    login(client, "approver@dev.local")
    assert client.put(f"/api/projects/{pid}/answers/1.3", json={"answer": "Yes"}).status_code == 403
    assert client.post("/api/projects", json={"name": "X"}).status_code == 403


def test_bad_input(client: TestClient) -> None:
    login(client, ADMIN_EMAIL)
    pid = project_id(client, "CFC Model")
    assert client.put(f"/api/projects/{pid}/answers/9.9", json={"answer": "Yes"}).status_code == 404
    assert (
        client.put(f"/api/projects/{pid}/answers/1.2", json={"answer": "Maybe"}).status_code == 422
    )
    long = "x" * 601
    assert (
        client.put(f"/api/projects/{pid}/answers/1.2", json={"evidence": long}).status_code == 422
    )
    assert (
        client.put(f"/api/projects/{pid}/answers/1.2", json={"evidence": "x" * 600}).status_code
        == 200
    )
    assert client.get("/api/projects/nope").status_code == 404
    assert client.post("/api/projects", json={"name": "   "}).status_code == 422
    assert client.post("/api/projects", json={"name": "A", "stage": "Done"}).status_code == 422
    assert (
        client.post("/api/projects", json={"name": "A", "owner_user_id": "nobody"}).status_code
        == 422
    )


def test_patch_and_archive(client: TestClient) -> None:
    login(client, "reviewer@dev.local")
    pid = project_id(client, "City Care Agent")
    r = client.patch(f"/api/projects/{pid}", json={"stage": "On hold", "sponsor": " Ko Aung "})
    assert r.json()["stage"] == "On hold" and r.json()["sponsor"] == "Ko Aung"
    assert client.patch(f"/api/projects/{pid}", json={"owner_user_id": None}).status_code == 422

    assert client.patch(f"/api/projects/{pid}", json={"archived": True}).json()["archived"]
    assert len(client.get("/api/projects").json()) == 11
    assert [p["name"] for p in client.get("/api/projects?archived=true").json()] == [
        "City Care Agent"
    ]
    # Archived projects keep their data but cannot be changed.
    assert client.put(f"/api/projects/{pid}/answers/1.1", json={"answer": "Yes"}).status_code == 409
    assert client.get(f"/api/projects/{pid}").status_code == 200

    login(client, ADMIN_EMAIL)
    pid2 = project_id(client, "CFC Model")
    me_owner = login(client, "owner@dev.local")
    assert client.patch(f"/api/projects/{pid2}", json={"archived": True}).status_code == 403
    login(client, ADMIN_EMAIL)
    r = client.patch(f"/api/projects/{pid2}", json={"owner_user_id": me_owner["id"]})
    assert r.json()["owner"]["name"] == "Test Owner"
    login(client, "owner@dev.local")
    assert client.get(f"/api/projects/{pid2}").json()["can_edit"]


def test_confirm_ai_answer(client: TestClient, db: Session) -> None:
    login(client, "owner@dev.local")
    pid = client.post("/api/projects", json={"name": "AI test"}).json()["id"]
    # Phase 3 writes AI answers; simulate one here.
    db.add(
        Answer(
            project_id=pid, question_id="5.4", answer="Partly", evidence="e", source="ai_interview"
        )
    )
    db.commit()
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["answers"][0]["confirmed"] is False

    r = client.post(f"/api/projects/{pid}/answers/5.4/confirm")
    assert r.json()["changed"] and r.json()["answer"]["confirmed"]
    assert r.json()["answer"]["source"] == "ai_interview"
    assert client.post(f"/api/projects/{pid}/answers/5.4/confirm").json()["changed"] is False
    assert client.get(f"/api/projects/{pid}/history").json()[0]["source"] == "confirm"
    assert client.post(f"/api/projects/{pid}/answers/5.5/confirm").status_code == 404

    # A person's edit also makes it theirs.
    db.add(Answer(project_id=pid, question_id="6.1", answer="Yes", source="ai_evidence"))
    db.commit()
    r = client.put(f"/api/projects/{pid}/answers/6.1", json={"answer": "Yes", "evidence": "mine"})
    assert r.json()["answer"]["source"] == "person" and r.json()["answer"]["confirmed"]
    row = db.scalar(select(Answer).where(Answer.project_id == pid, Answer.question_id == "6.1"))
    db.refresh(row)
    assert row.source == "person"
