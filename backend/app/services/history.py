"""Every answer change writes one answer_history row, in the same transaction."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ANSWER_SOURCES, Answer, AnswerHistory, Project, User


def save_answer(
    db: Session,
    project: Project,
    question_id: str,
    *,
    answer: str | None,
    evidence: str,
    source: str,
    user: User,
    confirmed_by: str | None = None,
) -> tuple[Answer, bool]:
    """Set an answer and record the change. Returns (row, changed). Caller commits."""
    row = db.get(Answer, (project.id, question_id))
    old_answer, old_evidence = (row.answer, row.evidence) if row else (None, "")
    same = row is not None and old_answer == answer and old_evidence == evidence
    # A person saving the same values is not an edit. The agent repeating itself is not either.
    if same and (source == "person" or (row.source == source and row.confirmed_by == confirmed_by)):
        return row, False
    if row is None:
        row = Answer(project_id=project.id, question_id=question_id)
        db.add(row)
    row.answer = answer
    row.evidence = evidence
    row.source = source
    # A person's edit makes the answer theirs. An AI answer is unconfirmed unless a
    # person accepted it (confirmed_by).
    row.confirmed_by = confirmed_by
    row.updated_by = user.id
    row.updated_at = datetime.now(UTC)
    project.updated_at = row.updated_at
    db.add(
        AnswerHistory(
            project_id=project.id,
            question_id=question_id,
            old_answer=old_answer,
            new_answer=answer,
            old_evidence=old_evidence,
            new_evidence=evidence,
            source=source,
            changed_by=user.id,
        )
    )
    return row, True


def confirm_answer(db: Session, row: Answer, user: User) -> bool:
    """A person accepts an AI answer as it is. Returns False if nothing to confirm."""
    if row.source == "person" or row.confirmed_by is not None:
        return False
    row.confirmed_by = user.id
    db.add(
        AnswerHistory(
            project_id=row.project_id,
            question_id=row.question_id,
            old_answer=row.answer,
            new_answer=row.answer,
            old_evidence=row.evidence,
            new_evidence=row.evidence,
            source="confirm",
            changed_by=user.id,
        )
    )
    return True


class UndoError(ValueError):
    pass


def undo_agent_answer(db: Session, project: Project, question_id: str, user: User) -> Answer:
    """Put back the answer from before the last agent change. Caller commits."""
    rows = db.scalars(
        select(AnswerHistory)
        .where(AnswerHistory.project_id == project.id, AnswerHistory.question_id == question_id)
        .order_by(AnswerHistory.id.desc())
    ).all()
    if not rows or rows[0].source not in ("ai_interview", "ai_evidence"):
        raise UndoError("There is no agent answer to undo for this question.")
    last = rows[0]
    row = db.get(Answer, (project.id, question_id))
    if row is None or row.answer != last.new_answer or row.evidence != last.new_evidence:
        raise UndoError("This answer changed after the agent recorded it.")
    before = next((h.source for h in rows[1:] if h.source in ANSWER_SOURCES), "person")
    current_answer, current_evidence = row.answer, row.evidence
    row.answer = last.old_answer
    row.evidence = last.old_evidence
    row.source = before if last.old_answer is not None else "person"
    row.confirmed_by = None
    row.updated_by = user.id
    row.updated_at = datetime.now(UTC)
    project.updated_at = row.updated_at
    db.add(
        AnswerHistory(
            project_id=project.id,
            question_id=question_id,
            old_answer=current_answer,
            new_answer=row.answer,
            old_evidence=current_evidence,
            new_evidence=row.evidence,
            source="undo",
            changed_by=user.id,
        )
    )
    return row
