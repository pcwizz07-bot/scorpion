from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import alerts, audit, devices, observations, stats

WEBUI_DIST = Path(__file__).resolve().parent.parent.parent / "webui" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Scorpion Backend", version="0.1.0", lifespan=lifespan)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    app.include_router(devices.router, prefix="/api/v1")
    app.include_router(observations.router, prefix="/api/v1")
    app.include_router(alerts.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")

    if WEBUI_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEBUI_DIST / "assets"), name="webui-assets")

        @app.get("/{full_path:path}")
        def serve_webui(full_path: str) -> FileResponse:
            candidate = WEBUI_DIST / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(WEBUI_DIST / "index.html")

    return app


app = create_app()
