"""Every answer change writes one answer_history row, in the same transaction."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import Answer, AnswerHistory, Project, User


def save_answer(
    db: Session,
    project: Project,
    question_id: str,
    *,
    answer: str | None,
    evidence: str,
    source: str,
    user: User,
) -> tuple[Answer, bool]:
    """Set an answer and record the change. Returns (row, changed). Caller commits."""
    row = db.get(Answer, (project.id, question_id))
    old_answer, old_evidence = (row.answer, row.evidence) if row else (None, "")
    if row is not None and old_answer == answer and old_evidence == evidence:
        return row, False
    if row is None:
        row = Answer(project_id=project.id, question_id=question_id)
        db.add(row)
    row.answer = answer
    row.evidence = evidence
    row.source = source
    # A person's edit makes the answer theirs; an AI answer starts unconfirmed.
    row.confirmed_by = None
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
