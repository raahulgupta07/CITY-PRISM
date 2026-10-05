from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import current_user
from app.db.base import get_db
from app.db.models import Dimension, User
from app.routers.schemas import DimensionOut, UserOut

router = APIRouter(tags=["framework"], dependencies=[Depends(current_user)])


@router.get("/questions", response_model=list[DimensionOut])
def questions(db: Session = Depends(get_db)) -> list[Dimension]:
    """The 8 dimensions, each with its 5 questions."""
    return list(
        db.scalars(
            select(Dimension)
            .options(selectinload(Dimension.questions))
            .order_by(Dimension.sort_order)
        ).all()
    )


@router.get("/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db)) -> list[User]:
    """For the owner picker."""
    return list(db.scalars(select(User).order_by(User.name)).all())
