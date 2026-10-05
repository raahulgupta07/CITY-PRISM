"""Shapes the model must reply with. A reply that does not fit is rejected."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.db.models import EVIDENCE_MAX

# The model writes "Don't know"; the database stores "Dont_know".
TO_DB = {"Yes": "Yes", "Partly": "Partly", "No": "No", "Don't know": "Dont_know"}
MAX_SUGGESTIONS = 15


def _short(v: Any) -> str:
    return str(v or "").strip()[:EVIDENCE_MAX]


class InterviewReply(BaseModel):
    answer: str = ""
    evidence: str = ""
    follow_up: str = Field(default="", alias="followUp")

    @field_validator("answer")
    @classmethod
    def _answer(cls, v: str) -> str:
        v = v.strip()
        if v and v not in TO_DB:
            raise ValueError("unknown answer")
        return v

    @field_validator("evidence", "follow_up", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return _short(v)

    def model_post_init(self, _context: Any) -> None:
        if not self.answer and not self.follow_up:
            raise ValueError("neither an answer nor a follow-up question")

    @property
    def db_answer(self) -> str | None:
        return TO_DB.get(self.answer)


class EvidenceItem(BaseModel):
    id: str
    answer: str
    evidence: str = ""


def parse_evidence_reply(data: Any, known_ids: set[str]) -> list[EvidenceItem]:
    """A JSON array of suggestions. Unknown IDs and invalid answers are dropped."""
    if isinstance(data, dict):  # some models wrap the array in an object
        lists = [v for v in data.values() if isinstance(v, list)]
        data = lists[0] if len(lists) == 1 else None
    if not isinstance(data, list):
        raise ValueError("expected a JSON array")
    items: list[EvidenceItem] = []
    seen: set[str] = set()
    for raw in data:
        if not isinstance(raw, dict):
            continue
        qid = str(raw.get("id", "")).strip()
        answer = str(raw.get("answer", "")).strip()
        if qid not in known_ids or qid in seen or answer not in ("Yes", "Partly", "No"):
            continue
        seen.add(qid)
        items.append(EvidenceItem(id=qid, answer=answer, evidence=_short(raw.get("evidence"))))
    return items[:MAX_SUGGESTIONS]
