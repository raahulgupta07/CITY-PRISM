"""Tables from SPEC section 4, plus ai_calls (the AI call log from section 6.1).

Scores are computed, never stored, except the rules snapshot inside a brief.
Nothing is deleted: projects are archived.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ROLES = ("owner", "reviewer", "approver", "admin")
STAGES = ("Idea", "Feasibility", "Build", "Pilot / UAT", "Production", "On hold")
MODES = ("plan", "assess")
ANSWERS = ("Yes", "Partly", "No", "Dont_know")
ANSWER_SOURCES = ("person", "ai_interview", "ai_evidence")
# History also records a confirm (AI answer accepted by a person) and an undo.
HISTORY_SOURCES = (*ANSWER_SOURCES, "confirm", "undo")
SUGGESTION_STATUSES = ("pending", "accepted", "dismissed")
AI_FEATURES = ("interview", "evidence", "brief", "summary")
VERDICTS = ("fix", "go", "ready", "not_assessed")
EVIDENCE_MAX = 600
DEFAULT_DUE_DATE = date(2026, 10, 30)


def _in(column: str, values: tuple[str, ...], nullable: bool = False) -> str:
    listed = ", ".join(f"'{v}'" for v in values)
    expr = f"{column} IN ({listed})"
    return f"{column} IS NULL OR {expr}" if nullable else expr


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(_in("role", ROLES), name="role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Dimension(Base):
    __tablename__ = "dimensions"
    __table_args__ = (CheckConstraint("id BETWEEN 1 AND 8", name="id_range"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(200))
    group_name: Mapped[str] = mapped_column(String(50))
    lead_question: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer)

    questions: Mapped[list[Question]] = relationship(
        back_populates="dimension", order_by="Question.number"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (CheckConstraint("number BETWEEN 1 AND 5", name="number_range"),)

    id: Mapped[str] = mapped_column(String(8), primary_key=True)  # "5.1"
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimensions.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    dimension: Mapped[Dimension] = relationship(back_populates="questions")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(_in("stage", STAGES), name="stage"),
        CheckConstraint(_in("mode", MODES), name="mode"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    business_unit: Mapped[str] = mapped_column(String(200), default="")
    sponsor: Mapped[str] = mapped_column(String(200), default="")
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    stage: Mapped[str] = mapped_column(String(20), default="Idea")
    mode: Mapped[str] = mapped_column(String(10), default="assess")
    due_date: Mapped[date | None] = mapped_column(Date)  # 2026-10-30 for assessments
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    owner: Mapped[User | None] = relationship()
    answers: Mapped[list[Answer]] = relationship(back_populates="project")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint(_in("answer", ANSWERS, nullable=True), name="answer"),
        CheckConstraint(_in("source", ANSWER_SOURCES), name="source"),
    )

    # The primary key is the unique (project_id, question_id) pair.
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    answer: Mapped[str | None] = mapped_column(String(10))
    evidence: Mapped[str] = mapped_column(String(EVIDENCE_MAX), default="")
    source: Mapped[str] = mapped_column(String(20), default="person")
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    project: Mapped[Project] = relationship(back_populates="answers")


class AnswerHistory(Base):
    __tablename__ = "answer_history"
    __table_args__ = (
        CheckConstraint(_in("old_answer", ANSWERS, nullable=True), name="old_answer"),
        CheckConstraint(_in("new_answer", ANSWERS, nullable=True), name="new_answer"),
        CheckConstraint(_in("source", HISTORY_SOURCES), name="source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    old_answer: Mapped[str | None] = mapped_column(String(10))
    new_answer: Mapped[str | None] = mapped_column(String(10))
    old_evidence: Mapped[str] = mapped_column(Text, default="")
    new_evidence: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    __table_args__ = (
        CheckConstraint(_in("answer", ANSWERS), name="answer"),
        CheckConstraint(_in("status", SUGGESTION_STATUSES), name="status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[str] = mapped_column(String(10))
    evidence: Mapped[str] = mapped_column(String(EVIDENCE_MAX), default="")
    source_excerpt: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(10), default="pending")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (CheckConstraint(_in("verdict", VERDICTS), name="verdict"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    # Snapshot of the rules result when the brief was written.
    verdict: Mapped[str] = mapped_column(String(20))
    lowest: Mapped[float | None] = mapped_column(Float)
    weakest: Mapped[list] = mapped_column(JSON, default=list)
    dimension_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    answered: Mapped[int] = mapped_column(Integer, default=0)
    # Written by AI.
    headline: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    actions: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(100), default="")
    content: Mapped[bytes | None] = mapped_column(LargeBinary)  # kept in our database
    text_extract: Mapped[str] = mapped_column(Text, default="")
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AICall(Base):
    """One row per call to the model: who, what, which model, tokens, cost, time."""

    __tablename__ = "ai_calls"
    __table_args__ = (CheckConstraint(_in("feature", AI_FEATURES), name="feature"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    feature: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(200))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
