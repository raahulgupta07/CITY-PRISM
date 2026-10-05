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


_SSO_COOKIE = "prism_sso"
_SSO_SALT = "prism.sso.v1"
_SSO_MAX_AGE = 600


def set_sso_pending(response: Response, data: dict) -> None:
    """Remember state, nonce and PKCE verifier between SSO start and callback."""
    serializer = URLSafeTimedSerializer(get_settings().secret_key, salt=_SSO_SALT)
    response.set_cookie(
        _SSO_COOKIE,
        serializer.dumps(data),
        max_age=_SSO_MAX_AGE,
        httponly=True,
        secure=get_settings().env == "prod",
        samesite="lax",  # sent on the top-level redirect back from the identity provider
        path="/api/auth/sso",
    )


def pop_sso_pending(request: Request, response: Response) -> dict | None:
    response.delete_cookie(_SSO_COOKIE, path="/api/auth/sso")
    token = request.cookies.get(_SSO_COOKIE)
    if not token:
        return None
    serializer = URLSafeTimedSerializer(get_settings().secret_key, salt=_SSO_SALT)
    try:
        data = serializer.loads(token, max_age=_SSO_MAX_AGE)
    except BadSignature:
        return None
    return data if isinstance(data, dict) else None


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
