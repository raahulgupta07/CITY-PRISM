"""One app: /api for the server, everything else serves the built screens."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.db.base import SessionLocal
from app.routers import auth, health


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.run_migrations_on_start:
        from app.db.migrate import upgrade_to_head

        upgrade_to_head()
    if settings.seed_on_start:
        from app.seed import run_seed

        with SessionLocal() as db:
            run_seed(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="City Prism",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.env != "prod" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.env != "prod" else None,
    )
    for router in (health.router, auth.router):
        app.include_router(router, prefix="/api")

    build_dir = settings.frontend_build_dir.resolve()

    @app.get("/api/{rest:path}", include_in_schema=False)
    def api_not_found(rest: str) -> None:
        raise HTTPException(404, "Not found.")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        # Serve a real file from the build if it exists, else the app shell.
        if path:
            candidate = (build_dir / path).resolve()
            if candidate.is_file() and candidate.is_relative_to(build_dir):
                return FileResponse(candidate)
        index = build_dir / "index.html"
        if not index.is_file():
            raise HTTPException(404, "The screens are not built. Run `npm run build`.")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
