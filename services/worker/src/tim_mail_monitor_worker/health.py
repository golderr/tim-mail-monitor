"""Health payload helpers for local development and monitoring."""

from __future__ import annotations

from datetime import datetime, timezone

from tim_mail_monitor_worker.config import get_settings


def get_health_payload() -> dict[str, object]:
    settings = get_settings()

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "mailbox_configured": bool(settings.tim_mailbox_address),
            "database_configured": bool(settings.database_url),
            "supabase_configured": bool(settings.supabase_url),
            "microsoft_graph_configured": bool(
                settings.microsoft_tenant_id
                and settings.microsoft_client_id
                and settings.microsoft_client_secret
            ),
            "graph_folders_configured": bool(settings.graph_mail_folders),
        },
    }
