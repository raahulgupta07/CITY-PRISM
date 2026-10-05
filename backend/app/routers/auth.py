from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.auth.provider import get_provider
from app.auth.session import clear_session, set_session
from app.db.base import get_db
from app.db.models import User
from app.routers.schemas import UserOut

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    email: str = ""


@router.get("/auth/options")
def auth_options(db: Session = Depends(get_db)) -> dict:
    return get_provider().options(db)


@router.post("/auth/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    user = get_provider().authenticate(db, body.model_dump())
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in failed. Please try again.")
    set_session(response, user.id)
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user
