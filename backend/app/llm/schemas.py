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


MAX_ACTIONS = 3
MAX_RISKS = 3


class BriefAction(BaseModel):
    question_id: str
    action: str
    owner: str


class BriefReply(BaseModel):
    headline: str
    summary: str
    actions: list[BriefAction]
    risks: list[str]


def parse_brief_reply(data: Any, known_ids: set[str]) -> BriefReply:
    """SPEC 6.4 reply. Needs a headline and a summary; bad actions and extras are dropped."""
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    headline = str(data.get("headline") or "").strip()[:300]
    summary = str(data.get("summary") or "").strip()[:1500]
    if not headline or not summary:
        raise ValueError("missing headline or summary")
    raw_actions = data.get("actions") or []
    raw_risks = data.get("risks") or []
    if not isinstance(raw_actions, list) or not isinstance(raw_risks, list):
        raise ValueError("actions and risks must be lists")
    actions: list[BriefAction] = []
    for raw in raw_actions:
        if not isinstance(raw, dict):
            continue
        qid = str(raw.get("question") or raw.get("question_id") or "").strip()
        action = str(raw.get("action") or "").strip()[:300]
        if qid not in known_ids or not action:
            continue
        owner = str(raw.get("owner") or "").strip()[:100] or "To assign"
        actions.append(BriefAction(question_id=qid, action=action, owner=owner))
    risks = [str(r).strip()[:300] for r in raw_risks if isinstance(r, str) and r.strip()]
    return BriefReply(
        headline=headline,
        summary=summary,
        actions=actions[:MAX_ACTIONS],
        risks=risks[:MAX_RISKS],
    )
