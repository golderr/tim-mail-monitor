"""Environment-backed configuration for the worker service."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from dotenv import load_dotenv

load_dotenv()

def _to_list(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()

    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    log_level: str
    app_port: int
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    microsoft_tenant_id: str
    microsoft_client_id: str
    microsoft_client_secret: str
    microsoft_graph_scope: str
    microsoft_graph_base_url: str
    tim_mailbox_address: str
    tim_mailbox_display_name: str
    graph_mail_folders: tuple[str, ...]
    graph_message_page_size: int
    graph_timeout_seconds: int
    sync_lookback_days: int
    sync_max_messages_per_folder: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name="tim-mail-monitor-worker",
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        app_port=int(os.getenv("WORKER_PORT", "8001")),
        database_url=os.getenv("DATABASE_URL", ""),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        microsoft_tenant_id=os.getenv("MICROSOFT_TENANT_ID", ""),
        microsoft_client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
        microsoft_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
        microsoft_graph_scope=os.getenv(
            "MICROSOFT_GRAPH_SCOPE", "https://graph.microsoft.com/.default"
        ),
        microsoft_graph_base_url=os.getenv(
            "MICROSOFT_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0"
        ).rstrip("/"),
        tim_mailbox_address=os.getenv("TIM_MAILBOX_ADDRESS", ""),
        tim_mailbox_display_name=os.getenv(
            "TIM_MAILBOX_DISPLAY_NAME", "Tim Principal Mailbox"
        ),
        graph_mail_folders=_to_list(os.getenv("GRAPH_MAIL_FOLDERS"))
        or ("Inbox", "SentItems"),
        graph_message_page_size=int(os.getenv("GRAPH_MESSAGE_PAGE_SIZE", "50")),
        graph_timeout_seconds=int(os.getenv("GRAPH_TIMEOUT_SECONDS", "30")),
        sync_lookback_days=int(os.getenv("SYNC_LOOKBACK_DAYS", "14")),
        sync_max_messages_per_folder=int(
            os.getenv("SYNC_MAX_MESSAGES_PER_FOLDER", "200")
        ),
    )
