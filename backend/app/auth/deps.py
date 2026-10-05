"""FastAPI dependencies for the signed-in user and role checks."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.session import session_user_id
from app.db.base import get_db
from app.db.models import ROLES, User


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    uid = session_user_id(request)
    return db.get(User, uid) if uid else None


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    unknown = set(roles) - set(ROLES)
    if unknown:
        raise ValueError(f"Unknown roles: {unknown}")

    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot do this.")
        return user

    return check
