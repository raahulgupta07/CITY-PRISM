"""Request and response shapes for the API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import EVIDENCE_MAX

Role = Literal["owner", "reviewer", "approver", "admin"]
Stage = Literal["Idea", "Feasibility", "Build", "Pilot / UAT", "Production", "On hold"]
Mode = Literal["plan", "assess"]
AnswerValue = Literal["Yes", "Partly", "No", "Dont_know"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str


class UserRef(BaseModel):
    id: str
    name: str


# ---- Framework ----


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dimension_id: int
    number: int
    text: str
    is_draft: bool
    active: bool
    version: int


class DimensionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    group_name: str
    lead_question: str
    sort_order: int
    questions: list[QuestionOut]


class QuestionUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=5, max_length=500)
    is_draft: bool | None = None

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class DimensionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    lead_question: str | None = Field(default=None, min_length=5, max_length=500)


# ---- Scores (computed by app.scoring) ----


class DimensionScoreOut(BaseModel):
    id: int
    score: float | None
    raw: float | None
    capped: bool
    has_no: bool
    answered: int
    band: str


class ScoreOut(BaseModel):
    dimensions: list[DimensionScoreOut]
    lowest: float | None
    weakest: list[int]
    verdict: str
    answered: int
    coverage: float
    partial: bool


# ---- Projects ----


class ProjectOut(BaseModel):
    id: str
    name: str
    business_unit: str
    sponsor: str
    owner: UserRef | None
    stage: str
    mode: str
    due_date: date | None
    archived: bool
    created_at: datetime
    updated_at: datetime
    can_edit: bool
    score: ScoreOut


class AnswerOut(BaseModel):
    question_id: str
    answer: str | None
    evidence: str
    source: str
    confirmed: bool  # False only for an AI answer no person has confirmed yet
    updated_by: UserRef | None
    updated_at: datetime


class ProjectDetailOut(ProjectOut):
    answers: list[AnswerOut]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    business_unit: str = Field(default="", max_length=200)
    sponsor: str = Field(default="", max_length=200)
    owner_user_id: str | None = None
    stage: Stage = "Idea"
    mode: Mode = "plan"
    due_date: date | None = None

    @field_validator("name", "business_unit", "sponsor")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    business_unit: str | None = Field(default=None, max_length=200)
    sponsor: str | None = Field(default=None, max_length=200)
    owner_user_id: str | None = None
    stage: Stage | None = None
    mode: Mode | None = None
    due_date: date | None = None
    archived: bool | None = None


class AnswerIn(BaseModel):
    answer: AnswerValue | None = None
    evidence: str = Field(default="", max_length=EVIDENCE_MAX)

    @field_validator("evidence")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class AnswerSaved(BaseModel):
    answer: AnswerOut
    score: ScoreOut
    changed: bool


class HistoryOut(BaseModel):
    id: int
    question_id: str
    old_answer: str | None
    new_answer: str | None
    old_evidence: str
    new_evidence: str
    source: str
    changed_by: UserRef | None
    changed_at: datetime


# ---- Admin ----


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    role: Role = "owner"

    @field_validator("name", "email")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
