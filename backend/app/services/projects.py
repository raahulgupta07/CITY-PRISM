"""Build project responses with scores computed by the rules in app.scoring."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Answer, Project, User
from app.routers.schemas import AnswerOut, ProjectDetailOut, ProjectOut, ScoreOut, UserRef
from app.scoring import VERDICT_ORDER, ScoreResult, score_project
from app.services.permissions import can_edit_project


def answers_map(answers: Iterable[Answer]) -> dict[str, str | None]:
    return {a.question_id: a.answer for a in answers}


def score_out(result: ScoreResult) -> ScoreOut:
    data = asdict(result)
    data.pop("dimension_scores", None)
    return ScoreOut.model_validate(data)


def _ref(user: User | None) -> UserRef | None:
    return UserRef(id=user.id, name=user.name) if user else None


def users_by_id(db: Session) -> dict[str, User]:
    return {u.id: u for u in db.scalars(select(User)).all()}


def answer_out(a: Answer, users: dict[str, User]) -> AnswerOut:
    return AnswerOut(
        question_id=a.question_id,
        answer=a.answer,
        evidence=a.evidence,
        source=a.source,
        confirmed=a.source == "person" or a.confirmed_by is not None,
        updated_by=_ref(users.get(a.updated_by or "")),
        updated_at=a.updated_at,
    )


def project_out(
    p: Project, answers: Sequence[Answer], users: dict[str, User], viewer: User
) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        business_unit=p.business_unit,
        sponsor=p.sponsor,
        owner=_ref(users.get(p.owner_user_id or "")),
        stage=p.stage,
        mode=p.mode,
        due_date=p.due_date,
        archived=p.archived,
        created_at=p.created_at,
        updated_at=p.updated_at,
        can_edit=can_edit_project(viewer, p),
        score=score_out(score_project(answers_map(answers))),
    )


def project_detail(db: Session, p: Project, viewer: User) -> ProjectDetailOut:
    users = users_by_id(db)
    answers = db.scalars(select(Answer).where(Answer.project_id == p.id)).all()
    base = project_out(p, answers, users, viewer)
    ordered = sorted(answers, key=lambda a: tuple(int(x) for x in a.question_id.split(".")))
    return ProjectDetailOut(**base.model_dump(), answers=[answer_out(a, users) for a in ordered])


def list_projects(
    db: Session,
    viewer: User,
    *,
    bu: list[str] | None = None,
    stage: list[str] | None = None,
    mode: list[str] | None = None,
    verdict: list[str] | None = None,
    owner: list[str] | None = None,
    mine: bool = False,
    archived: bool = False,
) -> list[ProjectOut]:
    query = select(Project).where(Project.archived == archived)
    if bu:
        query = query.where(Project.business_unit.in_(bu))
    if stage:
        query = query.where(Project.stage.in_(stage))
    if mode:
        query = query.where(Project.mode.in_(mode))
    if owner:
        query = query.where(Project.owner_user_id.in_(owner))
    if mine:
        query = query.where(Project.owner_user_id == viewer.id)
    projects = db.scalars(query).all()

    # Two queries in total, whatever the number of projects.
    by_project: dict[str, list[Answer]] = {p.id: [] for p in projects}
    if projects:
        rows = db.scalars(select(Answer).where(Answer.project_id.in_(list(by_project)))).all()
        for a in rows:
            by_project[a.project_id].append(a)
    users = users_by_id(db)

    out = [project_out(p, by_project[p.id], users, viewer) for p in projects]
    if verdict:
        out = [p for p in out if p.score.verdict in verdict]
    # Weakest first: fix -> go -> ready -> not assessed, then lowest score, then name.
    out.sort(
        key=lambda p: (
            VERDICT_ORDER[p.score.verdict],
            p.score.lowest if p.score.lowest is not None else 9,
            p.name.lower(),
        )
    )
    return out
