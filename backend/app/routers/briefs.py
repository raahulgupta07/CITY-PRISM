"""Decision brief (SPEC 5.4 and 6.4).

The rules in app.scoring decide the verdict and the scores first. The AI only
writes the headline, summary, actions and risks around that fixed result.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.db.base import get_db
from app.db.models import Answer, AnswerHistory, Brief, Dimension, Project, Question, User
from app.llm import client as llm
from app.llm.prompts import brief_prompt
from app.llm.schemas import parse_brief_reply
from app.routers.agent import _llm_error, _owner_name
from app.routers.projects import _editable, _project
from app.routers.schemas import BriefActionOut, BriefOut, DimensionScoreOut, UserRef
from app.scoring import score_project
from app.services import permissions as perm
from app.services.projects import answers_map, users_by_id

router = APIRouter(tags=["briefs"])


def _naive(value: datetime | None) -> datetime | None:
    # SQLite gives back naive UTC times; compare like with like.
    return value.astimezone(UTC).replace(tzinfo=None) if value and value.tzinfo else value


def _last_change(db: Session, project_id: str) -> datetime | None:
    return db.scalar(
        select(func.max(AnswerHistory.changed_at)).where(AnswerHistory.project_id == project_id)
    )


def brief_out(b: Brief, users: dict[str, User], last_change: datetime | None = None) -> BriefOut:
    def ref(user_id: str | None) -> UserRef | None:
        u = users.get(user_id) if user_id else None
        return UserRef(id=u.id, name=u.name) if u else None

    changed = last_change is not None and _naive(last_change) > _naive(b.created_at)
    return BriefOut(
        id=b.id,
        project_id=b.project_id,
        created_at=b.created_at,
        created_by=ref(b.created_by),
        verdict=b.verdict,
        lowest=b.lowest,
        weakest=b.weakest,
        dimensions=[DimensionScoreOut.model_validate(d) for d in b.dimension_scores.values()],
        answered=b.answered,
        headline=b.headline,
        summary=b.summary,
        actions=[BriefActionOut.model_validate(a) for a in b.actions],
        risks=b.risks,
        approved=b.approved,
        approved_by=ref(b.approved_by),
        approved_at=b.approved_at,
        changed_since=changed,
    )


@router.get("/projects/{project_id}/briefs", response_model=list[BriefOut])
def list_briefs(
    project_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(current_user),
) -> list[BriefOut]:
    project = _project(db, project_id)
    rows = db.scalars(
        select(Brief)
        .where(Brief.project_id == project.id)
        .order_by(Brief.created_at.desc(), Brief.id.desc())
    ).all()
    users = users_by_id(db)
    last = _last_change(db, project.id)
    return [brief_out(b, users, last) for b in rows]


@router.post(
    "/projects/{project_id}/briefs", response_model=BriefOut, status_code=status.HTTP_201_CREATED
)
def write_brief(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> BriefOut:
    project = _editable(db, project_id, user)
    rows = db.scalars(select(Answer).where(Answer.project_id == project.id)).all()
    # 1. The rules decide. This result is saved as the snapshot, whatever the AI writes.
    result = score_project(answers_map(rows))
    if result.verdict == "not_assessed":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Answer at least one question before writing a brief."
        )
    dimensions = list(db.scalars(select(Dimension).order_by(Dimension.sort_order)).all())
    questions = list(
        db.scalars(
            select(Question)
            .where(Question.active.is_(True))
            .order_by(Question.dimension_id, Question.number)
        ).all()
    )
    answers = {a.question_id: (a.answer, a.evidence) for a in rows}
    prompt = brief_prompt(project, _owner_name(db, project), dimensions, questions, answers, result)
    known = {q.id for q in questions}
    # 2. The AI writes the words around it.
    try:
        reply = llm.complete_json(
            prompt,
            lambda data: parse_brief_reply(data, known),
            kind="default",
            feature="brief",
            user_id=user.id,
            project_id=project.id,
            json_object=True,
        )
    except llm.LLMError as exc:
        raise _llm_error(exc) from exc

    brief = Brief(
        project_id=project.id,
        created_by=user.id,
        verdict=result.verdict,
        lowest=result.lowest,
        weakest=list(result.weakest),
        dimension_scores={
            str(d.id): DimensionScoreOut.model_validate(d, from_attributes=True).model_dump()
            for d in result.dimensions
        },
        answered=result.answered,
        headline=reply.headline,
        summary=reply.summary,
        actions=[a.model_dump() for a in reply.actions],
        risks=reply.risks,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return brief_out(brief, users_by_id(db))


@router.post("/briefs/{brief_id}/approve", response_model=BriefOut)
def approve_brief(
    brief_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> BriefOut:
    if not perm.can_approve_brief(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only approvers can approve a brief.")
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brief not found.")
    project = db.get(Project, brief.project_id)
    if project is None or project.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "This project is archived.")
    if brief.approved:
        raise HTTPException(status.HTTP_409_CONFLICT, "This brief is already approved.")
    brief.approved = True
    brief.approved_by = user.id
    brief.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(brief)
    return brief_out(brief, users_by_id(db), _last_change(db, project.id))
