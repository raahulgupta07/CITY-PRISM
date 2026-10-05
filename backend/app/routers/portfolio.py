"""Portfolio summary (SPEC 6.5, streamed) and export (SPEC 8)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.db.base import get_db
from app.db.models import User
from app.llm import client as llm
from app.llm.prompts import summary_prompt
from app.services import export
from app.services import permissions as perm

router = APIRouter(tags=["portfolio"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/portfolio/summary")
async def portfolio_summary(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> StreamingResponse:
    """Server-sent events: "text" pieces, then "done" or "error"."""
    try:
        llm.check_ready("default")
    except llm.LLMError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    dims, _questions, data = export.load(db)
    if not data:
        raise HTTPException(status.HTTP_409_CONFLICT, "There are no projects to summarise.")
    titles = {d.id: d.title for d in dims}
    prompt = summary_prompt(((d.project, d.result) for d in data), titles)
    user_id = user.id

    async def events() -> AsyncIterator[str]:
        try:
            async for piece in llm.stream_text(
                prompt, kind="default", feature="summary", user_id=user_id, project_id=None
            ):
                yield _sse("text", {"text": piece})
            yield _sse("done", {})
        except llm.LLMError as exc:
            yield _sse("error", {"message": exc.message})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _can_export(user: User) -> None:
    if not perm.can_export(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins can export the portfolio.")


def _download(body: bytes, ext: str, media_type: str) -> Response:
    name = f"city-prism-portfolio-{date.today().isoformat()}.{ext}"
    return Response(
        body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    _can_export(user)
    return _download(export.to_csv(db), "csv", "text/csv; charset=utf-8")


@router.get("/export.xlsx")
def export_xlsx(db: Session = Depends(get_db), user: User = Depends(current_user)) -> Response:
    _can_export(user)
    return _download(
        export.to_xlsx(db),
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
