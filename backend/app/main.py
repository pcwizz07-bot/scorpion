from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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

    # Serve the built SPA at /portal, same origin as the API (no CORS needed).
    # The webui has no client-side URL routing (tab state only), so a plain
    # static mount with html=True (index.html for directory requests) is
    # enough — no SPA-fallback catch-all route is required.
    if WEBUI_DIST.is_dir():
        app.mount("/portal", StaticFiles(directory=WEBUI_DIST, html=True), name="portal")

    return app


app = create_app()
