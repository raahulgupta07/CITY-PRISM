"""Company sign-in with OpenID Connect (authorization code flow with PKCE).

Works with any OIDC identity provider, such as Microsoft Entra ID. The browser
only follows redirects; the code exchange and token checks happen here.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import User

CALLBACK_PATH = "/api/auth/sso/callback"
_CACHE_SECONDS = 3600
_HTTP_TIMEOUT = 10.0
_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "ES256"]

# Tests swap this for an httpx.MockTransport.
transport: httpx.BaseTransport | None = None
_cache: dict[str, tuple[float, Any]] = {}


class SignInError(Exception):
    """Sign-in failed. `code` is a short reason the sign-in screen explains."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


@dataclass
class Pending:
    """What the start step remembers (in a short-lived signed cookie) for the callback."""

    state: str
    nonce: str
    verifier: str


def _get_json(url: str) -> dict:
    try:
        with httpx.Client(transport=transport, timeout=_HTTP_TIMEOUT) as client:
            r = client.get(url)
            r.raise_for_status()
            return r.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SignInError("provider", f"GET {url} failed: {exc}") from exc


def _cached(key: str, url: str, *, refresh: bool = False) -> dict:
    hit = _cache.get(key)
    if hit and not refresh and time.monotonic() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    data = _get_json(url)
    _cache[key] = (time.monotonic(), data)
    return data


def discovery() -> dict:
    issuer = get_settings().oidc_issuer
    return _cached("discovery", f"{issuer}/.well-known/openid-configuration")


def redirect_uri() -> str:
    return get_settings().public_url + CALLBACK_PATH


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def start() -> tuple[str, Pending]:
    """The URL to send the browser to, and what to remember for the callback."""
    settings = get_settings()
    pending = Pending(
        state=secrets.token_urlsafe(24),
        nonce=secrets.token_urlsafe(24),
        verifier=secrets.token_urlsafe(48),
    )
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": redirect_uri(),
        "scope": "openid email profile",
        "state": pending.state,
        "nonce": pending.nonce,
        "code_challenge": _b64(hashlib.sha256(pending.verifier.encode()).digest()),
        "code_challenge_method": "S256",
    }
    return f"{discovery()['authorization_endpoint']}?{urlencode(params)}", pending


def _exchange(code: str, pending: Pending) -> str:
    settings = get_settings()
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(),
        "client_id": settings.oidc_client_id,
        "code_verifier": pending.verifier,
    }
    if settings.oidc_client_secret:
        form["client_secret"] = settings.oidc_client_secret
    try:
        with httpx.Client(transport=transport, timeout=_HTTP_TIMEOUT) as client:
            r = client.post(discovery()["token_endpoint"], data=form)
    except httpx.HTTPError as exc:
        raise SignInError("provider", f"token request failed: {exc}") from exc
    if r.status_code != 200:
        raise SignInError("provider", f"token request returned {r.status_code}")
    token = r.json().get("id_token")
    if not isinstance(token, str):
        raise SignInError("provider", "no id_token in the token reply")
    return token


def _signing_key(token: str) -> Any:
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.PyJWTError as exc:
        raise SignInError("token", str(exc)) from exc
    jwks_uri = discovery()["jwks_uri"]
    for refresh in (False, True):  # the provider may have rotated its keys
        keys = jwt.PyJWKSet.from_dict(_cached("jwks", jwks_uri, refresh=refresh)).keys
        for key in keys:
            if kid is None or key.key_id == kid:
                return key.key
    raise SignInError("token", "no matching signing key")


def _claims(token: str, pending: Pending) -> dict:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            _signing_key(token),
            algorithms=_ALGORITHMS,
            audience=settings.oidc_client_id,
            issuer=discovery().get("issuer", settings.oidc_issuer),
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=60,
        )
    except jwt.PyJWTError as exc:
        raise SignInError("token", str(exc)) from exc
    if claims.get("nonce") != pending.nonce:
        raise SignInError("token", "nonce does not match")
    return claims


def _email(claims: dict) -> str:
    # Entra ID puts the work email in preferred_username when "email" is not issued.
    for key in ("email", "preferred_username", "upn"):
        value = str(claims.get(key) or "").strip().lower()
        if "@" in value:
            return value
    return ""


def finish(db: Session, code: str, state: str, pending: Pending) -> User:
    """Check the reply from the identity provider and return the signed-in user."""
    if not code or not secrets.compare_digest(state, pending.state):
        raise SignInError("expired", "state does not match")
    claims = _claims(_exchange(code, pending), pending)
    email = _email(claims)
    if not email:
        raise SignInError("no_email")
    settings = get_settings()
    domains = settings.allowed_domains
    if domains and email.rsplit("@", 1)[1] not in domains:
        raise SignInError("not_allowed", f"domain of {email} is not allowed")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        if not settings.oidc_create_users:
            raise SignInError("no_account", f"{email} has no account")
        name = str(claims.get("name") or "").strip()[:200] or email.split("@")[0]
        user = User(name=name, email=email, role="owner")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
