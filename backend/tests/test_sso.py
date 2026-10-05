"""Company sign-in (OIDC) against a fake identity provider."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from conftest import ADMIN_EMAIL
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.config import get_settings

ISSUER = "https://idp.test/tenant/v2.0"
CLIENT_ID = "prism-client"


class FakeIdP:
    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        self.jwks = {"keys": [{**jwk, "kid": "k1", "use": "sig", "alg": "RS256"}]}
        self.claims: dict = {}
        self.token_requests: list[dict] = []
        self.nonce = ""

    def id_token(self) -> str:
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "user-1",
            "iat": now,
            "exp": now + 600,
            "nonce": self.nonce,
            "name": "Aye Aye",
            "preferred_username": "Aye.Aye@cityholdings.com.mm",
            **self.claims,
        }
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "k1"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": "https://idp.test/authorize",
                    "token_endpoint": "https://idp.test/token",
                    "jwks_uri": "https://idp.test/keys",
                },
            )
        if path == "/keys":
            return httpx.Response(200, json=self.jwks)
        if path == "/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.token_requests.append(form)
            return httpx.Response(200, json={"id_token": self.id_token()})
        return httpx.Response(404)


@pytest.fixture
def idp(settings_env, monkeypatch: pytest.MonkeyPatch) -> FakeIdP:
    from app.auth import oidc

    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "s3cret")
    monkeypatch.setenv("PUBLIC_URL", "https://prism.test/")
    monkeypatch.setenv("OIDC_ALLOWED_DOMAINS", "cityholdings.com.mm")
    get_settings.cache_clear()
    fake = FakeIdP()
    monkeypatch.setattr(oidc, "transport", httpx.MockTransport(fake.handler))
    oidc._cache.clear()
    return fake


def start(client: TestClient, idp: FakeIdP) -> dict:
    r = client.get("/api/auth/sso/start", follow_redirects=False)
    assert r.status_code == 303
    url = urlparse(r.headers["location"])
    assert url.netloc == "idp.test" and url.path == "/authorize"
    params = {k: v[0] for k, v in parse_qs(url.query).items()}
    idp.nonce = params["nonce"]
    return params


def callback(client: TestClient, **params: str) -> httpx.Response:
    return client.get("/api/auth/sso/callback", params=params, follow_redirects=False)


def test_options_and_dev_login_off(client, idp):
    assert client.get("/api/auth/options").json() == {"provider": "oidc", "users": []}
    r = client.post("/api/auth/login", json={"email": ADMIN_EMAIL})
    assert r.status_code == 401


def test_new_staff_member_becomes_owner(client, idp):
    params = start(client, idp)
    assert params["client_id"] == CLIENT_ID
    assert params["redirect_uri"] == "https://prism.test/api/auth/sso/callback"
    assert params["code_challenge_method"] == "S256"
    r = callback(client, code="abc", state=params["state"])
    assert r.status_code == 303 and r.headers["location"] == "/"
    me = client.get("/api/me").json()
    assert me["email"] == "aye.aye@cityholdings.com.mm"
    assert me["name"] == "Aye Aye" and me["role"] == "owner"
    sent = idp.token_requests[0]
    assert sent["code"] == "abc" and sent["client_secret"] == "s3cret"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(sent["code_verifier"].encode()).digest())
    assert challenge.rstrip(b"=").decode() == params["code_challenge"]


def test_existing_user_keeps_role(client, idp):
    idp.claims = {"email": ADMIN_EMAIL.upper()}
    params = start(client, idp)
    callback(client, code="abc", state=params["state"])
    assert client.get("/api/me").json()["role"] == "admin"


def test_callback_is_single_use(client, idp):
    params = start(client, idp)
    callback(client, code="abc", state=params["state"])
    client.post("/api/auth/logout")
    r = callback(client, code="abc", state=params["state"])
    assert r.headers["location"] == "/signin?error=expired"
    assert client.get("/api/me").status_code == 401


@pytest.mark.parametrize(
    ("claims", "state_ok", "reason"),
    [
        ({"preferred_username": "someone@gmail.com"}, True, "not_allowed"),
        ({"preferred_username": None}, True, "no_email"),
        ({"nonce": "other"}, True, "token"),
        ({"aud": "another-app"}, True, "token"),
        ({"iss": "https://evil.test"}, True, "token"),
        ({"exp": int(time.time()) - 3600}, True, "token"),
        ({}, False, "expired"),
    ],
)
def test_refused(client, idp, claims, state_ok, reason):
    idp.claims = claims
    params = start(client, idp)
    r = callback(client, code="abc", state=params["state"] if state_ok else "wrong")
    assert r.headers["location"] == f"/signin?error={reason}"
    assert client.get("/api/me").status_code == 401


def test_forged_signature_refused(client, idp):
    params = start(client, idp)
    idp.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)  # not in JWKS
    r = callback(client, code="abc", state=params["state"])
    assert r.headers["location"] == "/signin?error=token"


def test_cancelled_at_provider(client, idp):
    start(client, idp)
    r = callback(client, error="access_denied")
    assert r.headers["location"] == "/signin?error=cancelled"


def test_no_account_when_creation_off(client, idp, monkeypatch):
    monkeypatch.setenv("OIDC_CREATE_USERS", "false")
    get_settings.cache_clear()
    params = start(client, idp)
    r = callback(client, code="abc", state=params["state"])
    assert r.headers["location"] == "/signin?error=no_account"


def test_sso_routes_off_without_settings(client):
    assert client.get("/api/auth/sso/start", follow_redirects=False).status_code == 404


def test_prod_needs_client_id_and_public_url(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.delenv("OIDC_CLIENT_ID", raising=False)
    with pytest.raises(ValueError, match="OIDC_CLIENT_ID"):
        Settings()
