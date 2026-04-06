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


def _to_str(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    normalized = value.strip()
    return normalized if normalized else default


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
    sync_overlap_minutes: int
    sync_max_messages_per_folder: int
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_reasoning_effort: str
    openai_text_verbosity: str
    classification_prompt_version: str
    classification_max_messages: int
    classification_event_min_confidence: float
    classification_overall_min_confidence: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name="tim-mail-monitor-worker",
        app_env=_to_str(os.getenv("APP_ENV"), "development"),
        log_level=_to_str(os.getenv("LOG_LEVEL"), "INFO"),
        app_port=int(os.getenv("WORKER_PORT", "8001")),
        database_url=_to_str(os.getenv("DATABASE_URL")),
        supabase_url=_to_str(os.getenv("SUPABASE_URL")),
        supabase_service_role_key=_to_str(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        microsoft_tenant_id=_to_str(os.getenv("MICROSOFT_TENANT_ID")),
        microsoft_client_id=_to_str(os.getenv("MICROSOFT_CLIENT_ID")),
        microsoft_client_secret=_to_str(os.getenv("MICROSOFT_CLIENT_SECRET")),
        microsoft_graph_scope=_to_str(
            os.getenv("MICROSOFT_GRAPH_SCOPE"), "https://graph.microsoft.com/.default"
        ),
        microsoft_graph_base_url=_to_str(
            os.getenv("MICROSOFT_GRAPH_BASE_URL"), "https://graph.microsoft.com/v1.0"
        ).rstrip("/"),
        tim_mailbox_address=_to_str(os.getenv("TIM_MAILBOX_ADDRESS")),
        tim_mailbox_display_name=_to_str(
            os.getenv("TIM_MAILBOX_DISPLAY_NAME"), "Tim Principal Mailbox"
        ),
        graph_mail_folders=_to_list(os.getenv("GRAPH_MAIL_FOLDERS"))
        or ("Inbox", "SentItems"),
        graph_message_page_size=int(os.getenv("GRAPH_MESSAGE_PAGE_SIZE", "50")),
        graph_timeout_seconds=int(os.getenv("GRAPH_TIMEOUT_SECONDS", "30")),
        sync_lookback_days=int(os.getenv("SYNC_LOOKBACK_DAYS", "14")),
        sync_overlap_minutes=int(os.getenv("SYNC_OVERLAP_MINUTES", "5")),
        sync_max_messages_per_folder=int(
            os.getenv("SYNC_MAX_MESSAGES_PER_FOLDER", "200")
        ),
        openai_api_key=_to_str(os.getenv("OPENAI_API_KEY")),
        openai_base_url=_to_str(
            os.getenv("OPENAI_BASE_URL"), "https://api.openai.com/v1"
        ),
        openai_model=_to_str(os.getenv("OPENAI_MODEL"), "gpt-5.4"),
        openai_reasoning_effort=_to_str(os.getenv("OPENAI_REASONING_EFFORT"), "low"),
        openai_text_verbosity=_to_str(os.getenv("OPENAI_TEXT_VERBOSITY"), "low"),
        classification_prompt_version=_to_str(
            os.getenv("CLASSIFICATION_PROMPT_VERSION"), "thread-review-v4"
        ),
        classification_max_messages=int(
            os.getenv("CLASSIFICATION_MAX_MESSAGES", "8")
        ),
        classification_event_min_confidence=float(
            os.getenv("CLASSIFICATION_EVENT_MIN_CONFIDENCE", "0.65")
        ),
        classification_overall_min_confidence=float(
            os.getenv("CLASSIFICATION_OVERALL_MIN_CONFIDENCE", "0.7")
        ),
    )
