"""FastAPI application factory.  Run:  uvicorn app.main:app --port 8080  (or: python run.py)"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import articles, insights, overview, revisions, scenario, snapshots


@asynccontextmanager
async def lifespan(_: FastAPI):
    if config.DEFAULT_SNAPSHOT.exists():
        snapshots.ingest(config.DEFAULT_SNAPSHOT.read_bytes(), config.DEFAULT_SNAPSHOT.name)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="IKEA SPI Supply Intelligence API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
    for module in (snapshots, overview, insights, articles, revisions, scenario):
        app.include_router(module.router)

    @app.get("/api/health", tags=["meta"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
