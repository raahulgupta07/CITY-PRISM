"""Admin only: the question set, users and roles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.db.base import get_db
from app.db.models import AICall, Dimension, Question, User
from app.routers.schemas import (
    DimensionUpdate,
    QuestionOut,
    QuestionUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])


@router.put("/questions/{question_id}", response_model=QuestionOut)
def update_question(
    question_id: str, body: QuestionUpdate, db: Session = Depends(get_db)
) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    if body.text is not None and body.text != question.text:
        question.text = body.text
        question.version += 1  # a new wording is a new version
    if body.is_draft is not None:
        question.is_draft = body.is_draft
    db.commit()
    return question


@router.put("/dimensions/{dimension_id}")
def update_dimension(
    dimension_id: int, body: DimensionUpdate, db: Session = Depends(get_db)
) -> dict:
    dimension = db.get(Dimension, dimension_id)
    if dimension is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dimension not found.")
    if body.title is not None:
        dimension.title = body.title.strip()
    if body.lead_question is not None:
        dimension.lead_question = body.lead_question.strip()
    db.commit()
    return {"id": dimension.id, "title": dimension.title, "lead_question": dimension.lead_question}


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> User:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists.")
    user = User(name=body.name, email=email, role=body.role)
    db.add(user)
    db.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if body.role is not None and body.role != user.role:
        if user.role == "admin":
            admins = db.scalar(select(func.count()).select_from(User).where(User.role == "admin"))
            if admins <= 1:
                raise HTTPException(status.HTTP_409_CONFLICT, "Keep at least one admin.")
        user.role = body.role
    if body.name is not None:
        user.name = body.name.strip()
    db.commit()
    return user


@router.get("/ai-calls")
def ai_calls(
    limit: int = Query(default=200, ge=1, le=1000), db: Session = Depends(get_db)
) -> list[dict]:
    """The AI call log, newest first. No prompt or reply text is stored."""
    rows = db.scalars(select(AICall).order_by(AICall.id.desc()).limit(limit)).all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "project_id": r.project_id,
            "feature": r.feature,
            "model": r.model,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "cost_usd": r.cost_usd,
            "latency_ms": r.latency_ms,
            "ok": r.ok,
            "error": r.error,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
