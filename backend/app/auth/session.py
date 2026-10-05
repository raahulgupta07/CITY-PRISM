"""Signed session cookie. It holds only the user ID."""

from __future__ import annotations

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import get_settings

COOKIE = "prism_session"
_SALT = "prism.session.v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SALT)


def set_session(response: Response, user_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        COOKIE,
        _serializer().dumps({"uid": user_id}),
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.env == "prod",
        samesite="lax",
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def session_user_id(request: Request) -> str | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=get_settings().session_max_age)
    except BadSignature:  # also covers an expired cookie
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return uid if isinstance(uid, str) else None
