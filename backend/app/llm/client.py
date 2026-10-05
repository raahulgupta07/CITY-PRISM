"""The only place that calls the AI model. Server side only; the key never leaves it.

One call, one ai_calls row (user, project, feature, model, tokens, cost, time),
whether the call worked or not. No automatic retries.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Any, Literal, TypeVar

import httpx

from app.config import get_settings
from app.db.base import SessionLocal
from app.db.models import AICall

ModelKind = Literal["fast", "default"]
T = TypeVar("T")

# Tests swap this for an httpx.MockTransport.
transport: httpx.BaseTransport | None = None


class LLMError(Exception):
    """A friendly message for the screen, plus a short code for the log."""

    def __init__(self, message: str, code: str, status: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


NOT_SET_UP = LLMError("The AI is not set up yet. Please ask the City AI team.", "not_set_up", 503)
UNREADABLE = "The AI reply could not be read. Nothing was saved. Please try again."


def model_for(kind: ModelKind) -> str:
    s = get_settings()
    return s.llm_model_fast if kind == "fast" else s.llm_model_default


def _log(
    *,
    user_id: str | None,
    project_id: str | None,
    feature: str,
    model: str,
    usage: dict | None,
    latency_ms: int,
    error: str = "",
) -> None:
    usage = usage or {}
    with SessionLocal() as db:  # own session: the log is kept even if the request fails
        db.add(
            AICall(
                user_id=user_id,
                project_id=project_id,
                feature=feature,
                model=model,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                cost_usd=usage.get("cost"),
                latency_ms=latency_ms,
                ok=not error,
                error=error[:500],
            )
        )
        db.commit()


def parse_json(text: str) -> Any:
    """Read JSON from a model reply, allowing a ``` fence around it."""
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    return json.loads(cleaned)


def complete_json(
    prompt: str,
    validate: Callable[[Any], T],
    *,
    kind: ModelKind,
    feature: str,
    user_id: str | None,
    project_id: str | None,
    json_object: bool = False,
) -> T:
    """Send one prompt; return the reply checked by `validate`, or raise LLMError.

    `validate` raises ValueError (pydantic's ValidationError is one) when the reply
    does not match the expected shape. Then nothing is saved.
    """
    settings = get_settings()
    model = model_for(kind)
    if not settings.openrouter_api_key or not model:
        raise NOT_SET_UP

    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "usage": {"include": True},
    }
    if json_object:
        body["response_format"] = {"type": "json_object"}

    started = time.perf_counter()
    usage: dict | None = None
    try:
        with httpx.Client(transport=transport, timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                json=body,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "X-Title": "City Prism",
                },
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        if response.status_code != 200:
            _log(
                user_id=user_id,
                project_id=project_id,
                feature=feature,
                model=model,
                usage=None,
                latency_ms=elapsed,
                error=f"http_{response.status_code}",
            )
            raise LLMError(
                "The AI service did not answer. Please try again later.",
                f"http_{response.status_code}",
            )
        data = response.json()
        usage = data.get("usage")
        content = data["choices"][0]["message"]["content"] or ""
    except httpx.TimeoutException as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        _log(
            user_id=user_id,
            project_id=project_id,
            feature=feature,
            model=model,
            usage=None,
            latency_ms=elapsed,
            error="timeout",
        )
        raise LLMError("The AI took too long to answer. Please try again.", "timeout", 504) from exc
    except httpx.HTTPError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        _log(
            user_id=user_id,
            project_id=project_id,
            feature=feature,
            model=model,
            usage=None,
            latency_ms=elapsed,
            error="network",
        )
        raise LLMError(
            "The AI service could not be reached. Please try again later.", "network"
        ) from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        _log(
            user_id=user_id,
            project_id=project_id,
            feature=feature,
            model=model,
            usage=usage,
            latency_ms=elapsed,
            error="bad_response",
        )
        raise LLMError(UNREADABLE, "bad_response") from exc

    try:
        parsed = parse_json(content)
    except ValueError as exc:
        _log(
            user_id=user_id,
            project_id=project_id,
            feature=feature,
            model=model,
            usage=usage,
            latency_ms=elapsed,
            error="invalid_json",
        )
        raise LLMError(UNREADABLE, "invalid_json") from exc
    try:
        result = validate(parsed)
    except ValueError as exc:
        _log(
            user_id=user_id,
            project_id=project_id,
            feature=feature,
            model=model,
            usage=usage,
            latency_ms=elapsed,
            error="invalid_schema",
        )
        raise LLMError(UNREADABLE, "invalid_schema") from exc

    _log(
        user_id=user_id,
        project_id=project_id,
        feature=feature,
        model=model,
        usage=usage,
        latency_ms=elapsed,
    )
    return result
