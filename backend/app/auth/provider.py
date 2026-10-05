"""Sign-in providers (SPEC section 10)."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import User


class AuthProvider(Protocol):
    name: str

    def options(self, db: Session) -> dict:
        """What the sign-in screen needs to show."""
        ...

    def authenticate(self, db: Session, payload: dict) -> User | None:
        """Return the signed-in user, or None if sign-in failed."""
        ...


class DevSSOProvider:
    """Development stub: pick any existing user. Never enabled with ENV=prod."""

    name = "dev"

    def options(self, db: Session) -> dict:
        users = db.scalars(select(User).order_by(User.role, User.name)).all()
        return {
            "provider": self.name,
            "users": [{"name": u.name, "email": u.email, "role": u.role} for u in users],
        }

    def authenticate(self, db: Session, payload: dict) -> User | None:
        email = str(payload.get("email", "")).strip().lower()
        if not email:
            return None
        return db.scalar(select(User).where(User.email == email))


class OidcProvider:
    """Company sign-in. The browser goes to /api/auth/sso/start; see app/auth/oidc.py."""

    name = "oidc"

    def options(self, db: Session) -> dict:
        return {"provider": self.name, "users": []}

    def authenticate(self, db: Session, payload: dict) -> User | None:
        return None  # only the SSO callback signs people in


class NoProvider:
    """Production without OIDC settings: nobody can sign in."""

    name = "none"

    def options(self, db: Session) -> dict:
        return {"provider": self.name, "users": []}

    def authenticate(self, db: Session, payload: dict) -> User | None:
        return None


def get_provider() -> AuthProvider:
    settings = get_settings()
    if settings.oidc_issuer:
        return OidcProvider()
    if settings.env == "prod":
        return NoProvider()
    return DevSSOProvider()
