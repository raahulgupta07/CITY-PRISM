from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.db.base import get_db
from app.db.models import DEFAULT_DUE_DATE, Answer, AnswerHistory, Project, Question, User
from app.routers.schemas import (
    AnswerIn,
    AnswerSaved,
    HistoryOut,
    ProjectCreate,
    ProjectDetailOut,
    ProjectOut,
    ProjectUpdate,
    UserRef,
)
from app.scoring import score_project
from app.services import permissions as perm
from app.services.history import confirm_answer, save_answer
from app.services.projects import (
    answer_out,
    answers_map,
    list_projects,
    project_detail,
    score_out,
    users_by_id,
)

router = APIRouter(tags=["projects"])


def _project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    return project


def _editable(db: Session, project_id: str, user: User) -> Project:
    project = _project(db, project_id)
    if not perm.can_edit_project(user, project):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot change this project.")
    if project.archived:
        raise HTTPException(status.HTTP_409_CONFLICT, "This project is archived.")
    return project


def _check_owner(db: Session, owner_id: str | None) -> None:
    if owner_id is not None and db.get(User, owner_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown project owner.")


@router.get("/projects", response_model=list[ProjectOut])
def get_projects(
    bu: list[str] = Query(default=[]),
    stage: list[str] = Query(default=[]),
    mode: list[str] = Query(default=[]),
    verdict: list[str] = Query(default=[]),
    owner: list[str] = Query(default=[]),
    mine: bool = False,
    archived: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[ProjectOut]:
    return list_projects(
        db,
        user,
        bu=bu,
        stage=stage,
        mode=mode,
        verdict=verdict,
        owner=owner,
        mine=mine,
        archived=archived,
    )


@router.post("/projects", response_model=ProjectDetailOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> ProjectDetailOut:
    if not perm.can_create_project(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot create projects.")
    if not body.name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a project name.")
    owner_id = body.owner_user_id or user.id
    _check_owner(db, owner_id)
    due = body.due_date
    if due is None and body.mode == "assess":
        due = DEFAULT_DUE_DATE
    project = Project(
        name=body.name,
        business_unit=body.business_unit,
        sponsor=body.sponsor,
        owner_user_id=owner_id,
        stage=body.stage,
        mode=body.mode,
        due_date=due,
    )
    db.add(project)
    db.commit()
    return project_detail(db, project, user)


@router.get("/projects/{project_id}", response_model=ProjectDetailOut)
def get_project(
    project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)
) -> ProjectDetailOut:
    return project_detail(db, _project(db, project_id), user)


@router.patch("/projects/{project_id}", response_model=ProjectDetailOut)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ProjectDetailOut:
    project = _project(db, project_id)
    changes = body.model_dump(exclude_unset=True)
    if "archived" in changes:
        if not perm.can_archive_project(user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot archive projects.")
        project.archived = bool(changes.pop("archived"))
    if changes:
        if not perm.can_edit_project(user, project):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot change this project.")
        if project.archived:
            raise HTTPException(status.HTTP_409_CONFLICT, "This project is archived.")
        if "owner_user_id" in changes:
            if changes["owner_user_id"] is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an owner.")
            _check_owner(db, changes["owner_user_id"])
        if "name" in changes and not (changes["name"] or "").strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Enter a project name.")
        for key, value in changes.items():
            setattr(project, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    return project_detail(db, project, user)


@router.put("/projects/{project_id}/answers/{question_id}", response_model=AnswerSaved)
def put_answer(
    project_id: str,
    question_id: str,
    body: AnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AnswerSaved:
    project = _editable(db, project_id, user)
    if db.get(Question, question_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")
    row, changed = save_answer(
        db,
        project,
        question_id,
        answer=body.answer,
        evidence=body.evidence,
        source="person",
        user=user,
    )
    db.commit()
    return _saved(db, project, row, changed)


@router.post("/projects/{project_id}/answers/{question_id}/confirm", response_model=AnswerSaved)
def confirm(
    project_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AnswerSaved:
    project = _editable(db, project_id, user)
    row = db.get(Answer, (project.id, question_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This question has no answer yet.")
    changed = confirm_answer(db, row, user)
    db.commit()
    return _saved(db, project, row, changed)


def _saved(db: Session, project: Project, row: Answer, changed: bool) -> AnswerSaved:
    answers = db.scalars(select(Answer).where(Answer.project_id == project.id)).all()
    return AnswerSaved(
        answer=answer_out(row, users_by_id(db)),
        score=score_out(score_project(answers_map(answers))),
        changed=changed,
    )


@router.get("/projects/{project_id}/history", response_model=list[HistoryOut])
def history(
    project_id: str,
    question_id: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(current_user),
) -> list[HistoryOut]:
    _project(db, project_id)
    query = select(AnswerHistory).where(AnswerHistory.project_id == project_id)
    if question_id:
        query = query.where(AnswerHistory.question_id == question_id)
    rows = db.scalars(
        query.order_by(AnswerHistory.changed_at.desc(), AnswerHistory.id.desc()).limit(limit)
    ).all()
    users = users_by_id(db)
    return [
        HistoryOut(
            id=h.id,
            question_id=h.question_id,
            old_answer=h.old_answer,
            new_answer=h.new_answer,
            old_evidence=h.old_evidence,
            new_evidence=h.new_evidence,
            source=h.source,
            changed_by=UserRef(id=u.id, name=u.name)
            if (u := users.get(h.changed_by or ""))
            else None,
            changed_at=h.changed_at,
        )
        for h in rows
    ]
