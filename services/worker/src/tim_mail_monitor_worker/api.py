"""FastAPI application entrypoint for the worker service."""

from __future__ import annotations

from fastapi import FastAPI

from tim_mail_monitor_worker.config import get_settings
from tim_mail_monitor_worker.health import get_health_payload


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Tim Mail Monitor Worker",
        version="0.1.0",
        description="Milestone 2 worker scaffold for mailbox ingestion.",
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "message": "Milestone 2 mailbox ingestion worker is running.",
        }

    @app.get("/health")
    async def health() -> dict[str, object]:
        return get_health_payload()

    return app


app = create_app()
