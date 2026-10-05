"""Load the framework, the default admin and the 12 projects from SPEC section 9.

Safe to run many times: it only adds what is missing and never overwrites
edits made in the app. Run with `python -m app.seed`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.base import SessionLocal
from app.db.models import (
    DEFAULT_DUE_DATE,
    Answer,
    AnswerHistory,
    Dimension,
    Project,
    Question,
    User,
)
from app.framework import DIMENSIONS

ADMIN = ("Rahul Gupta", "rahulgupta@cityholdings.com.mm", "admin")

# Sign-in test users for development only (ENV=dev). Never seeded in production.
DEV_USERS = [
    ("Test Owner", "owner@dev.local", "owner"),
    ("Test Reviewer", "reviewer@dev.local", "reviewer"),
    ("Test Approver", "approver@dev.local", "approver"),
]

# (name, business unit, sponsor, stage, {question: (answer, evidence)})
PROJECTS: list[tuple[str, str, str, str, dict[str, tuple[str, str]]]] = [
    (
        "Employee Assistant",
        "Hypertrade",
        "Thar Htet",
        "Feasibility",
        {
            "2.1": ("Yes", "Business owner is the Chief People Officer."),
            "2.2": ("No", "Tech and AI team know, but the BU / function does not know yet."),
            "2.3": ("Yes", "Steering Committee has authority to clear bottlenecks."),
            "2.4": ("Yes", "CHL IT and DAAI IT have committed."),
            "2.5": ("Yes", "Funding plan beyond the pilot is in place."),
            "5.1": ("No", "Business owner has not set the quality %."),
            "5.2": ("Yes", ""),
            "5.3": ("Yes", ""),
        },
    ),
    (
        "CFC Model",
        "Food & Beverage",
        "",
        "Build",
        {
            "1.1": (
                "Partly",
                "Expected output not yet agreed; a stakeholder meeting is needed "
                "before optimising.",
            ),
            "3.2": (
                "No",
                "Waiting for the data CFC agreed to send. No movement since the 10 Aug meeting.",
            ),
        },
    ),
    (
        "Fresh Replenishment",
        "Retail / CMHL",
        "",
        "Build",
        {
            "3.3": ("No", "49% of vegetable SKUs have no expiry or shelf-life data."),
            "2.4": (
                "Partly",
                "Waiting for a timeslot from the CMHL IT head to review the model output.",
            ),
        },
    ),
    (
        "Future Fields Forecasting",
        "Future Fields (SG)",
        "",
        "Build",
        {
            "3.3": (
                "Partly",
                "Only stock-out and return data is available (sales = stock-out minus return).",
            ),
            "5.2": (
                "Partly",
                "Tested: sales prediction error rose from 2.8% to above 14% from August.",
            ),
        },
    ),
    (
        "Ferry Optimisation (pilot)",
        "Hub / Group",
        "Ma Swe",
        "Pilot / UAT",
        {
            "2.1": ("Yes", "Ma Swe leads the project."),
            "3.2": ("Yes", "Optimisation model built on CHL hub data."),
            "7.3": (
                "Partly",
                "Ma Swe will arrange a session with the ferry team to share results "
                "and agree the pilot.",
            ),
        },
    ),
    (
        "Consumer Insights (City Agent Insights)",
        "Distribution",
        "",
        "Pilot / UAT",
        {
            "5.2": ("Yes", "UAT and testing completed by the PG team."),
            "7.3": ("Yes", "PG team ran the UAT."),
        },
    ),
    (
        "City Agent Insights + Databot",
        "Hub / Group",
        "",
        "Pilot / UAT",
        {
            "5.2": ("Partly", "Finance is testing it on their own financial data."),
            "7.3": ("Partly", "Finance team is testing it now."),
        },
    ),
    (
        "ITSM Agent (ARIA)",
        "All sectors",
        "",
        "Production",
        {
            "7.5": ("Partly", "Live and announced to sectors; adoption is now the focus."),
        },
    ),
    (
        "CityGPT Next (City Squad)",
        "Hub / Group",
        "",
        "Build",
        {
            "4.2": ("Partly", "Platform credentials not issued in mid-Sep; launch moved to 9 Oct."),
            "7.1": (
                "Partly",
                "City Agent Pro training started with Finance; other teams by availability.",
            ),
        },
    ),
    ("RO & ED Digital Conversion", "Distribution", "", "Production", {}),
    ("Coverage Planning (MCP) Tool", "Distribution", "", "Production", {}),
    ("City Care Agent", "Retail / CMHL", "", "Production", {}),
]


def _ensure_user(db: Session, name: str, email: str, role: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=name, email=email, role=role)
        db.add(user)
        db.flush()
    return user


def seed_framework(db: Session) -> None:
    for order, (dim_id, title, group, lead, draft, texts) in enumerate(DIMENSIONS, start=1):
        if db.get(Dimension, dim_id) is None:
            db.add(
                Dimension(
                    id=dim_id, title=title, group_name=group, lead_question=lead, sort_order=order
                )
            )
        for number, text in enumerate(texts, start=1):
            qid = f"{dim_id}.{number}"
            if db.get(Question, qid) is None:
                db.add(
                    Question(
                        id=qid,
                        dimension_id=dim_id,
                        number=number,
                        text=text,
                        is_draft=draft,
                        active=True,
                        version=1,
                    )
                )
    db.flush()


def seed_projects(db: Session, owner: User) -> None:
    for name, bu, sponsor, stage, answers in PROJECTS:
        if db.scalar(select(Project).where(Project.name == name)) is not None:
            continue
        project = Project(
            name=name,
            business_unit=bu,
            sponsor=sponsor,
            owner_user_id=owner.id,
            stage=stage,
            mode="assess",
            due_date=DEFAULT_DUE_DATE,
        )
        db.add(project)
        db.flush()
        for qid, (answer, evidence) in answers.items():
            db.add(
                Answer(
                    project_id=project.id,
                    question_id=qid,
                    answer=answer,
                    evidence=evidence,
                    source="person",
                    updated_by=owner.id,
                )
            )
            db.add(
                AnswerHistory(
                    project_id=project.id,
                    question_id=qid,
                    old_answer=None,
                    new_answer=answer,
                    old_evidence="",
                    new_evidence=evidence,
                    source="person",
                    changed_by=owner.id,
                )
            )
    db.flush()


def run_seed(db: Session) -> None:
    seed_framework(db)
    admin = _ensure_user(db, *ADMIN)
    if get_settings().env in ("dev", "test"):
        for user in DEV_USERS:
            _ensure_user(db, *user)
    seed_projects(db, admin)
    db.commit()


def main() -> None:
    from app.db.migrate import upgrade_to_head

    upgrade_to_head()
    with SessionLocal() as db:
        run_seed(db)
    print("Seed done.")


if __name__ == "__main__":
    main()
