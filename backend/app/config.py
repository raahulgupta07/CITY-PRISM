"""Settings from the environment. See .env.example."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DEV_SECRET = "dev-only-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    data_dir: Path = BACKEND_DIR / "data"
    # Empty means SQLite in data_dir. Set a postgresql+psycopg:// URL to switch.
    database_url: str = ""
    secret_key: str = DEV_SECRET
    session_max_age: int = 60 * 60 * 12
    frontend_build_dir: Path = REPO_DIR / "build"
    run_migrations_on_start: bool = True
    seed_on_start: bool = True

    # Used from phase 3. The key never leaves the server.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model_fast: str = ""
    llm_model_default: str = ""
    llm_timeout_seconds: float = 60.0

    # Company sign-in (OpenID Connect, e.g. Microsoft Entra ID). Empty issuer = off.
    public_url: str = ""
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    # Comma-separated email domains allowed to sign in. Empty = any account the issuer accepts.
    oidc_allowed_domains: str = ""
    # Create a project owner account the first time a staff member signs in.
    oidc_create_users: bool = True

    @model_validator(mode="after")
    def _check(self) -> Settings:
        if self.env == "prod" and self.secret_key in ("", DEV_SECRET):
            raise ValueError("Set SECRET_KEY before running with ENV=prod.")
        if not self.secret_key:
            self.secret_key = DEV_SECRET
        if self.oidc_issuer and not (self.oidc_client_id and self.public_url):
            raise ValueError("Set OIDC_CLIENT_ID and PUBLIC_URL to use OIDC_ISSUER.")
        self.public_url = self.public_url.rstrip("/")
        self.oidc_issuer = self.oidc_issuer.rstrip("/")
        return self

    @property
    def allowed_domains(self) -> set[str]:
        parts = self.oidc_allowed_domains.split(",")
        return {p.strip().lower().lstrip("@") for p in parts if p.strip()}

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.data_dir / 'prism.db'}"

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
