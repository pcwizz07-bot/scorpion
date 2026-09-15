from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import devices, observations


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
    return app


app = create_app()
