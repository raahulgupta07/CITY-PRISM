from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import oidc
from app.auth.deps import current_user
from app.auth.provider import get_provider
from app.auth.session import clear_session, pop_sso_pending, set_session, set_sso_pending
from app.config import get_settings
from app.db.base import get_db
from app.db.models import User
from app.routers.schemas import UserOut

router = APIRouter(tags=["auth"])
log = logging.getLogger("prism.auth")


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


def _require_sso() -> None:
    if not get_settings().oidc_issuer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company sign-in is not set up.")


@router.get("/auth/sso/start", include_in_schema=False)
def sso_start() -> RedirectResponse:
    _require_sso()
    try:
        url, pending = oidc.start()
    except oidc.SignInError as exc:
        log.warning("SSO start failed: %s", exc)
        return RedirectResponse(f"/signin?error={exc.code}", status.HTTP_303_SEE_OTHER)
    response = RedirectResponse(url, status.HTTP_303_SEE_OTHER)
    set_sso_pending(response, asdict(pending))
    return response


@router.get("/auth/sso/callback", include_in_schema=False)
def sso_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
) -> RedirectResponse:
    _require_sso()
    response = RedirectResponse("/", status.HTTP_303_SEE_OTHER)
    data = pop_sso_pending(request, response)
    try:
        if error:  # the person cancelled, or the identity provider refused
            raise oidc.SignInError("cancelled", f"identity provider error: {error[:100]}")
        if data is None:
            raise oidc.SignInError("expired", "no or expired SSO cookie")
        user = oidc.finish(db, code, state, oidc.Pending(**data))
    except (oidc.SignInError, TypeError) as exc:
        reason = exc.code if isinstance(exc, oidc.SignInError) else "expired"
        log.warning("SSO sign-in failed (%s): %s", reason, exc)
        response.headers["location"] = f"/signin?error={reason}"
        return response
    log.info("SSO sign-in: %s", user.email)
    set_session(response, user.id)
    return response


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user
