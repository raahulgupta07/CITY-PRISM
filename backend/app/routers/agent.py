"""The agent (SPEC 6): Interview, Read evidence, suggestions and Undo.

AI suggests, people decide. The AI never sets a score or a verdict: answers it
writes are saved with source ai_* and the rules in app.scoring do the rest.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.db.base import get_db
from app.db.models import AISuggestion, Answer, Dimension, EvidenceFile, Project, Question, User
from app.llm import client as llm
from app.llm.prompts import evidence_prompt, interview_prompt
from app.llm.schemas import InterviewReply, parse_evidence_reply
from app.routers.projects import _editable, _project, _saved
from app.routers.schemas import (
    AcceptAllOut,
    AnswerSaved,
    EvidenceOut,
    InterviewIn,
    InterviewOut,
    SuggestionDone,
    SuggestionOut,
)
from app.scoring import score_project
from app.services.extract_text import ExtractError, extract_text
from app.services.history import UndoError, save_answer, undo_agent_answer
from app.services.projects import answer_out, answers_map, score_out, users_by_id

router = APIRouter(tags=["agent"])

MAX_PROMPT_CHARS = 24_000


def _owner_name(db: Session, project: Project) -> str:
    owner = db.get(User, project.owner_user_id) if project.owner_user_id else None
    return owner.name if owner else "Not set"


def _llm_error(exc: llm.LLMError) -> HTTPException:
    return HTTPException(exc.status, exc.message)


@router.post("/projects/{project_id}/agent/interview", response_model=InterviewOut)
def interview(
    project_id: str,
    body: InterviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> InterviewOut:
    project = _editable(db, project_id, user)
    question = db.get(Question, body.question_id)
    if question is None or not question.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    dimension = db.get(Dimension, question.dimension_id)
    prompt = interview_prompt(
        project,
        _owner_name(db, project),
        dimension,
        question,
        body.reply.strip(),
        body.context.strip(),
    )
    try:
        reply = llm.complete_json(
            prompt,
            InterviewReply.model_validate,
            kind="fast",
            feature="interview",
            user_id=user.id,
            project_id=project.id,
            json_object=True,
        )
    except llm.LLMError as exc:
        raise _llm_error(exc) from exc

    saved: AnswerSaved | None = None
    if reply.db_answer:
        row, changed = save_answer(
            db,
            project,
            question.id,
            answer=reply.db_answer,
            evidence=reply.evidence,
            source="ai_interview",
            user=user,
        )
        db.commit()
        saved = _saved(db, project, row, changed)
    return InterviewOut(
        answer=reply.answer, evidence=reply.evidence, followUp=reply.follow_up, saved=saved
    )


@router.post("/projects/{project_id}/answers/{question_id}/undo", response_model=AnswerSaved)
def undo(
    project_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AnswerSaved:
    project = _editable(db, project_id, user)
    try:
        row = undo_agent_answer(db, project, question_id, user)
    except UndoError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    return _saved(db, project, row, True)


@router.post("/projects/{project_id}/agent/evidence", response_model=EvidenceOut)
async def read_evidence(
    project_id: str,
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> EvidenceOut:
    project = _editable(db, project_id, user)
    parts: list[str] = []
    filename = "Pasted text"
    content: bytes | None = None
    content_type = "text/plain"
    if file is not None and file.filename:
        content = await file.read()
        filename = file.filename[:300]
        content_type = (file.content_type or "")[:100]
        try:
            parts.append(extract_text(filename, content))
        except ExtractError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if text.strip():
        parts.append(text.strip())
        if content is None:
            content = text.strip().encode()
    if not parts:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Paste some text or choose a file first."
        )
    full_text = "\n\n".join(parts)

    # The text and the file stay in our database, whatever the AI does next.
    evidence = EvidenceFile(
        project_id=project.id,
        filename=filename,
        content_type=content_type,
        content=content,
        text_extract=full_text,
        uploaded_by=user.id,
    )
    db.add(evidence)
    db.commit()

    questions = db.scalars(
        select(Question)
        .where(Question.active.is_(True))
        .order_by(Question.dimension_id, Question.number)
    ).all()
    current = answers_map(db.scalars(select(Answer).where(Answer.project_id == project.id)).all())
    sent = full_text[:MAX_PROMPT_CHARS]
    prompt = evidence_prompt(project, _owner_name(db, project), questions, current, sent)
    known = {q.id for q in questions}
    try:
        items = llm.complete_json(
            prompt,
            lambda data: parse_evidence_reply(data, known),
            kind="default",
            feature="evidence",
            user_id=user.id,
            project_id=project.id,
        )
    except llm.LLMError as exc:
        raise _llm_error(exc) from exc

    created: list[AISuggestion] = []
    for item in items:
        if current.get(item.id) == item.answer:
            continue  # already the answer: nothing to suggest
        # A newer reading replaces older open suggestions for the same question.
        for old in db.scalars(
            select(AISuggestion).where(
                AISuggestion.project_id == project.id,
                AISuggestion.question_id == item.id,
                AISuggestion.status == "pending",
            )
        ).all():
            old.status = "dismissed"
        suggestion = AISuggestion(
            project_id=project.id,
            question_id=item.id,
            answer=item.answer,
            evidence=item.evidence,
            source_excerpt=filename,
            created_by=user.id,
        )
        db.add(suggestion)
        created.append(suggestion)
    db.commit()
    return EvidenceOut(
        file_id=evidence.id,
        filename=filename,
        chars_read=len(sent),
        truncated=len(full_text) > MAX_PROMPT_CHARS,
        suggestions=[SuggestionOut.model_validate(s) for s in created],
    )


@router.get("/projects/{project_id}/suggestions", response_model=list[SuggestionOut])
def list_suggestions(
    project_id: str,
    status_filter: str = "pending",
    db: Session = Depends(get_db),
    _user: User = Depends(current_user),
) -> list[AISuggestion]:
    _project(db, project_id)
    return list(
        db.scalars(
            select(AISuggestion)
            .where(AISuggestion.project_id == project_id, AISuggestion.status == status_filter)
            .order_by(AISuggestion.created_at, AISuggestion.question_id)
        ).all()
    )


def _pending(db: Session, suggestion_id: str, user: User) -> tuple[AISuggestion, Project]:
    suggestion = db.get(AISuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suggestion not found.")
    project = _editable(db, suggestion.project_id, user)
    if suggestion.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "This suggestion was already handled.")
    return suggestion, project


def _accept(db: Session, s: AISuggestion, project: Project, user: User) -> Answer:
    # Accepting is a person's decision, so the answer counts as confirmed by them.
    row, _ = save_answer(
        db,
        project,
        s.question_id,
        answer=s.answer,
        evidence=s.evidence,
        source="ai_evidence",
        user=user,
        confirmed_by=user.id,
    )
    s.status = "accepted"
    return row


@router.post("/suggestions/{suggestion_id}/accept", response_model=SuggestionDone)
def accept(
    suggestion_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> SuggestionDone:
    suggestion, project = _pending(db, suggestion_id, user)
    row = _accept(db, suggestion, project, user)
    db.commit()
    return SuggestionDone(
        suggestion=SuggestionOut.model_validate(suggestion),
        saved=_saved(db, project, row, True),
    )


@router.post("/suggestions/{suggestion_id}/dismiss", response_model=SuggestionDone)
def dismiss(
    suggestion_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> SuggestionDone:
    suggestion, _project_row = _pending(db, suggestion_id, user)
    suggestion.status = "dismissed"
    db.commit()
    return SuggestionDone(suggestion=SuggestionOut.model_validate(suggestion), saved=None)


@router.post("/projects/{project_id}/suggestions/accept-all", response_model=AcceptAllOut)
def accept_all(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> AcceptAllOut:
    project = _editable(db, project_id, user)
    pending = db.scalars(
        select(AISuggestion).where(
            AISuggestion.project_id == project.id, AISuggestion.status == "pending"
        )
    ).all()
    rows = [_accept(db, s, project, user) for s in pending]
    db.commit()
    users = users_by_id(db)
    answers = db.scalars(select(Answer).where(Answer.project_id == project.id)).all()
    return AcceptAllOut(
        accepted=len(rows),
        answers=[answer_out(r, users) for r in rows],
        score=score_out(score_project(answers_map(answers))),
    )
