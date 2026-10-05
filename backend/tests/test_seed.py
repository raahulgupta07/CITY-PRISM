from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Answer, AnswerHistory, Dimension, Project, Question, User
from app.scoring import score_project
from app.seed import run_seed

EXPECTED = {
    "Employee Assistant": "go",
    "CFC Model": "fix",
    "Fresh Replenishment": "fix",
    "Future Fields Forecasting": "go",
    "Ferry Optimisation (pilot)": "go",
    "Consumer Insights (City Agent Insights)": "ready",
    "City Agent Insights + Databot": "go",
    "ITSM Agent (ARIA)": "go",
    "CityGPT Next (City Squad)": "go",
    "RO & ED Digital Conversion": "not_assessed",
    "Coverage Planning (MCP) Tool": "not_assessed",
    "City Care Agent": "not_assessed",
}


def _verdicts(db: Session) -> dict[str, str]:
    out = {}
    for p in db.scalars(select(Project)).all():
        answers = {a.question_id: a.answer for a in p.answers}
        out[p.name] = score_project(answers).verdict
    return out


def test_framework(db: Session) -> None:
    assert db.scalar(select(func.count()).select_from(Dimension)) == 8
    questions = db.scalars(select(Question)).all()
    assert len(questions) == 40
    drafts = sorted(q.id for q in questions if q.is_draft)
    assert drafts == [f"{d}.{n}" for d in (1, 2) for n in range(1, 6)]


def test_projects_and_verdicts(db: Session) -> None:
    assert _verdicts(db) == EXPECTED
    projects = db.scalars(select(Project)).all()
    assert {p.mode for p in projects} == {"assess"}
    assert {str(p.due_date) for p in projects} == {"2026-10-30"}
    admin = db.scalar(select(User).where(User.email == "rahulgupta@cityholdings.com.mm"))
    assert admin is not None and admin.role == "admin"
    assert {p.owner_user_id for p in projects} == {admin.id}
    consumer = next(p for p in projects if p.name.startswith("Consumer Insights"))
    assert score_project({a.question_id: a.answer for a in consumer.answers}).partial


def test_answers_are_from_people_and_in_history(db: Session) -> None:
    answers = db.scalars(select(Answer)).all()
    assert len(answers) == 24
    assert {a.source for a in answers} == {"person"}
    assert db.scalar(select(func.count()).select_from(AnswerHistory)) == 24


def test_seed_runs_twice_without_changes(db: Session) -> None:
    question = db.get(Question, "5.1")
    question.text = "Edited by the admin."
    db.commit()
    run_seed(db)
    run_seed(db)
    assert db.scalar(select(func.count()).select_from(Project)) == 12
    assert db.scalar(select(func.count()).select_from(Answer)) == 24
    assert db.scalar(select(func.count()).select_from(User)) == 4
    assert db.get(Question, "5.1").text == "Edited by the admin."
