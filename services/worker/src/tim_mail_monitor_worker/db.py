"""Postgres helpers for mailbox ingestion persistence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tim_mail_monitor_worker.config import Settings, get_settings
from tim_mail_monitor_worker.event_detector import RULE_VERSION, URGENT_EVENT_TYPES
from tim_mail_monitor_worker.models import (
    NormalizedAttachment,
    NormalizedMessage,
    NormalizedRecipient,
    TriggeredEvent,
)

EVENT_PRIORITY: tuple[str, ...] = (
    "deadline",
    "draft_needed",
    "meeting_request",
    "scope_change",
    "client_materials",
    "status_request",
    "commitment",
    "cancellation_pause",
    "proposal_request",
    "new_project",
)
EVENT_PRIORITY_MAP = {event_type: index for index, event_type in enumerate(EVENT_PRIORITY)}
PROJECT_NUMBER_PATTERNS = (
    re.compile(r"\bp[#:\-\s]?(\d{4,8})\b", re.IGNORECASE),
    re.compile(r"\bproject\s+#?(\d{4,8})\b", re.IGNORECASE),
)
TRACKED_HISTORY_FIELDS = (
    "system_event_tags",
    "event_tags",
    "system_primary_event_tag",
    "primary_event_tag",
    "system_promotion_state",
    "promotion_state",
    "system_reply_state",
    "reply_state",
    "system_is_urgent",
    "is_urgent",
    "review_state",
    "first_opened_at",
    "latest_correspondence_at",
    "client_display_name",
    "client_names",
    "project_number",
    "correspondent_display_name",
    "latest_correspondence_direction",
    "no_consulting_staff_attached",
    "system_card_header",
    "card_header",
    "system_summary",
    "summary",
)


@dataclass(frozen=True)
class MailboxConfigRecord:
    id: str
    mailbox_address: str
    display_name: str | None
    initial_sync_lookback_days: int
    last_successful_sync_at: datetime | None


@dataclass
class SyncCounters:
    messages_seen: int = 0
    messages_inserted: int = 0
    messages_updated: int = 0
    threads_touched: int = 0
    recipients_upserted: int = 0
    attachments_upserted: int = 0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def connect_db(settings: Settings) -> psycopg.Connection[Any]:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def ensure_mailbox_config(
    conn: psycopg.Connection[Any],
    *,
    mailbox_address: str,
    display_name: str | None,
    initial_sync_lookback_days: int,
) -> MailboxConfigRecord:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.mailbox_configs (
              mailbox_address,
              display_name,
              initial_sync_lookback_days,
              is_active,
              polling_enabled
            )
            values (%s, %s, %s, true, true)
            on conflict (mailbox_address) do update
            set display_name = coalesce(excluded.display_name, public.mailbox_configs.display_name),
                initial_sync_lookback_days = excluded.initial_sync_lookback_days,
                updated_at = timezone('utc', now())
            returning id, mailbox_address, display_name, initial_sync_lookback_days, last_successful_sync_at
            """,
            (mailbox_address, display_name, initial_sync_lookback_days),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("Failed to load or create mailbox_config.")

    return MailboxConfigRecord(
        id=str(row["id"]),
        mailbox_address=row["mailbox_address"],
        display_name=row["display_name"],
        initial_sync_lookback_days=row["initial_sync_lookback_days"],
        last_successful_sync_at=row["last_successful_sync_at"],
    )


def get_internal_domains(
    conn: psycopg.Connection[Any], *, mailbox_address: str
) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select domain
            from public.internal_domains
            where is_active = true
            """
        )
        rows = cur.fetchall()

    domains = {str(row["domain"]).lower() for row in rows}
    mailbox_domain = mailbox_address.split("@")[-1].strip().lower()
    if mailbox_domain:
        domains.add(mailbox_domain)
    return domains


def create_sync_run(
    conn: psycopg.Connection[Any],
    *,
    mailbox_config_id: str,
    folders: tuple[str, ...],
    checkpoint_start: datetime,
    trigger_source: str = "manual",
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.sync_runs (
              mailbox_config_id,
              trigger_source,
              status,
              folders,
              checkpoint_start,
              started_at
            )
            values (%s, %s, 'running', %s, %s, timezone('utc', now()))
            returning id
            """,
            (mailbox_config_id, trigger_source, Jsonb(list(folders)), checkpoint_start),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("Failed to create sync_runs row.")

    return str(row["id"])


def fail_running_sync_runs(
    conn: psycopg.Connection[Any],
    *,
    mailbox_config_id: str,
    reason: str,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            update public.sync_runs
            set status = 'failed',
                error_text = %s,
                completed_at = timezone('utc', now())
            where mailbox_config_id = %s
              and status = 'running'
            """,
            (reason, mailbox_config_id),
        )
        return cur.rowcount


def complete_sync_run(
    conn: psycopg.Connection[Any],
    *,
    sync_run_id: str,
    mailbox_config_id: str,
    counters: SyncCounters,
    checkpoint_end: datetime,
    error_text: str | None = None,
) -> None:
    status = "failed" if error_text else "completed"
    completed_at = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            update public.sync_runs
            set status = %s,
                checkpoint_end = %s,
                messages_seen = %s,
                messages_inserted = %s,
                messages_updated = %s,
                threads_touched = %s,
                recipients_upserted = %s,
                attachments_upserted = %s,
                error_text = %s,
                completed_at = %s
            where id = %s
            """,
            (
                status,
                checkpoint_end,
                counters.messages_seen,
                counters.messages_inserted,
                counters.messages_updated,
                counters.threads_touched,
                counters.recipients_upserted,
                counters.attachments_upserted,
                error_text,
                completed_at,
                sync_run_id,
            ),
        )
        cur.execute(
            """
            update public.mailbox_configs
            set last_attempted_sync_at = %s,
                last_successful_sync_at = case
                  when %s = 'completed' then %s
                  else last_successful_sync_at
                end,
                last_error_text = %s
            where id = %s
            """,
            (
                completed_at,
                status,
                completed_at,
                error_text,
                mailbox_config_id,
            ),
        )


def upsert_thread_record(
    conn: psycopg.Connection[Any],
    *,
    mailbox_config_id: str,
    thread_key: str,
    conversation_id: str | None,
    normalized_subject: str | None,
    latest_subject: str | None,
    message_timestamp: datetime | None,
    direction: str,
) -> str:
    last_inbound_at = message_timestamp if direction == "inbound" else None
    last_outbound_at = message_timestamp if direction == "outbound" else None

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.thread_records (
              mailbox_config_id,
              thread_key,
              conversation_id,
              normalized_subject,
              latest_subject,
              first_message_at,
              last_message_at,
              last_inbound_at,
              last_outbound_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (mailbox_config_id, thread_key) do update
            set conversation_id = coalesce(public.thread_records.conversation_id, excluded.conversation_id),
                normalized_subject = coalesce(excluded.normalized_subject, public.thread_records.normalized_subject),
                latest_subject = coalesce(excluded.latest_subject, public.thread_records.latest_subject),
                updated_at = timezone('utc', now())
            returning id
            """,
            (
                mailbox_config_id,
                thread_key,
                conversation_id,
                normalized_subject,
                latest_subject,
                message_timestamp,
                message_timestamp,
                last_inbound_at,
                last_outbound_at,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("Failed to upsert thread_records row.")

    return str(row["id"])


def upsert_message(
    conn: psycopg.Connection[Any],
    *,
    mailbox_config_id: str,
    thread_record_id: str,
    message: NormalizedMessage,
) -> tuple[str, bool]:
    insert_params = (
        mailbox_config_id,
        thread_record_id,
        message.graph_message_id,
        message.internet_message_id,
        message.conversation_id,
        message.conversation_index,
        message.parent_folder_id,
        message.folder_name,
        message.direction,
        message.sender_email,
        message.sender_name,
        message.sender_is_internal,
        message.sender_is_external,
        message.sender_matched_internal_domain,
        message.subject,
        message.normalized_subject,
        message.body_preview,
        message.body_text,
        message.body_content_type,
        message.created_at_graph,
        message.sent_at,
        message.received_at,
        message.last_modified_at_graph,
        message.is_read,
        message.is_draft,
        message.has_attachments,
        message.importance,
        message.flag_status,
        message.inference_classification,
        Jsonb(message.categories),
        message.web_link,
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.messages (
              mailbox_config_id,
              thread_record_id,
              graph_message_id,
              internet_message_id,
              conversation_id,
              conversation_index,
              parent_folder_id,
              folder_name,
              direction,
              sender_email,
              sender_name,
              sender_is_internal,
              sender_is_external,
              sender_matched_internal_domain,
              subject,
              normalized_subject,
              body_preview,
              body_text,
              body_content_type,
              created_at_graph,
              sent_at,
              received_at,
              last_modified_at_graph,
              is_read,
              is_draft,
              has_attachments,
              importance,
              flag_status,
              inference_classification,
              categories,
              web_link
            )
            values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s
            )
            on conflict (mailbox_config_id, graph_message_id) do nothing
            returning id
            """,
            insert_params,
        )
        row = cur.fetchone()
        if row is not None:
            return str(row["id"]), True

        cur.execute(
            """
            update public.messages
            set thread_record_id = %s,
                internet_message_id = %s,
                conversation_id = %s,
                conversation_index = %s,
                parent_folder_id = %s,
                folder_name = %s,
                direction = %s,
                sender_email = %s,
                sender_name = %s,
                sender_is_internal = %s,
                sender_is_external = %s,
                sender_matched_internal_domain = %s,
                subject = %s,
                normalized_subject = %s,
                body_preview = %s,
                body_text = %s,
                body_content_type = %s,
                created_at_graph = %s,
                sent_at = %s,
                received_at = %s,
                last_modified_at_graph = %s,
                is_read = %s,
                is_draft = %s,
                has_attachments = %s,
                importance = %s,
                flag_status = %s,
                inference_classification = %s,
                categories = %s,
                web_link = %s,
                updated_at = timezone('utc', now())
            where mailbox_config_id = %s
              and graph_message_id = %s
            returning id
            """,
            (
                thread_record_id,
                message.internet_message_id,
                message.conversation_id,
                message.conversation_index,
                message.parent_folder_id,
                message.folder_name,
                message.direction,
                message.sender_email,
                message.sender_name,
                message.sender_is_internal,
                message.sender_is_external,
                message.sender_matched_internal_domain,
                message.subject,
                message.normalized_subject,
                message.body_preview,
                message.body_text,
                message.body_content_type,
                message.created_at_graph,
                message.sent_at,
                message.received_at,
                message.last_modified_at_graph,
                message.is_read,
                message.is_draft,
                message.has_attachments,
                message.importance,
                message.flag_status,
                message.inference_classification,
                Jsonb(message.categories),
                message.web_link,
                mailbox_config_id,
                message.graph_message_id,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("Failed to upsert messages row.")

    return str(row["id"]), False


def replace_message_recipients(
    conn: psycopg.Connection[Any],
    *,
    message_id: str,
    recipients: list[NormalizedRecipient],
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "delete from public.message_recipients where message_id = %s",
            (message_id,),
        )
        for recipient in recipients:
            cur.execute(
                """
                insert into public.message_recipients (
                  message_id,
                  recipient_type,
                  email,
                  display_name,
                  is_internal,
                  is_external,
                  matched_internal_domain
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    message_id,
                    recipient.recipient_type,
                    recipient.email,
                    recipient.display_name,
                    recipient.is_internal,
                    recipient.is_external,
                    recipient.matched_internal_domain,
                ),
            )
    return len(recipients)


def replace_attachments(
    conn: psycopg.Connection[Any],
    *,
    message_id: str,
    attachments: list[NormalizedAttachment],
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "delete from public.attachments where message_id = %s",
            (message_id,),
        )
        for attachment in attachments:
            cur.execute(
                """
                insert into public.attachments (
                  message_id,
                  graph_attachment_id,
                  name,
                  content_type,
                  size_bytes,
                  is_inline,
                  content_id,
                  last_modified_at_graph,
                  storage_mode,
                  reference_payload
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    message_id,
                    attachment.graph_attachment_id,
                    attachment.name,
                    attachment.content_type,
                    attachment.size_bytes,
                    attachment.is_inline,
                    attachment.content_id,
                    attachment.last_modified_at_graph,
                    attachment.storage_mode,
                    Jsonb(attachment.reference_payload),
                ),
            )
    return len(attachments)


def replace_communication_events(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    message_id: str,
    events: list[TriggeredEvent],
) -> int:
    deduped_events: dict[str, TriggeredEvent] = {}
    for event in events:
        if event.event_type in deduped_events:
            continue
        deduped_events[event.event_type] = event

    with conn.cursor() as cur:
        cur.execute(
            """
            delete from public.communication_events
            where message_id = %s
            """,
            (message_id,),
        )
        for event in deduped_events.values():
            cur.execute(
                """
                insert into public.communication_events (
                  thread_record_id,
                  message_id,
                  event_type,
                  status,
                  payload,
                  decision_source,
                  decision_version,
                  confidence
                )
                values (%s, %s, %s, 'detected', %s, %s, %s, %s)
                """,
                (
                    thread_record_id,
                    message_id,
                    event.event_type,
                    Jsonb(
                        {
                            "label": event.label,
                            "severity": event.severity,
                            "matched_terms": list(event.matched_terms),
                        }
                    ),
                    event.decision_source,
                    event.decision_version,
                    event.confidence,
                ),
            )
    return len(deduped_events)


def iter_messages_for_trigger_backfill(
    conn: psycopg.Connection[Any],
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              m.id::text as message_id,
              m.thread_record_id::text as thread_record_id,
              m.direction,
              m.sender_email::text as sender_email,
              m.subject,
              m.normalized_subject,
              m.body_preview,
              m.body_text,
              m.body_content_type,
              m.folder_name,
              m.created_at_graph,
              m.sent_at,
              m.received_at,
              m.last_modified_at_graph,
              m.has_attachments,
              m.is_read,
              m.is_draft,
              m.importance,
              m.flag_status,
              m.inference_classification,
              m.web_link,
              m.graph_message_id,
              m.internet_message_id,
              m.conversation_id,
              m.conversation_index,
              m.parent_folder_id
            from public.messages m
            order by coalesce(m.received_at, m.sent_at, m.created_at_graph)
            """
        )
        return list(cur.fetchall())


def _coerce_json_compatible(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return value
    return value


def _normalize_whitespace(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split())
    return normalized[:280] if normalized else None


def _normalize_email(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip().lower()
    return normalized or None


def _collect_internal_thread_emails(
    messages: list[dict[str, Any]],
    *,
    recipient_map: dict[str, list[dict[str, Any]]],
    internal_domains: set[str],
) -> set[str]:
    internal_emails: set[str] = set()

    for message in messages:
        sender_email = _normalize_email(message["sender_email"])
        if sender_email and (
            message.get("sender_is_internal") is True
            or _is_internal_email(sender_email, internal_domains)
        ):
            internal_emails.add(sender_email)

        for recipient in recipient_map.get(message["id"], []):
            recipient_email = _normalize_email(recipient["email"])
            if recipient_email and recipient["is_internal"]:
                internal_emails.add(recipient_email)

    return internal_emails


def _derive_no_consulting_staff_attached(
    messages: list[dict[str, Any]],
    *,
    recipient_map: dict[str, list[dict[str, Any]]],
    internal_domains: set[str],
    non_consulting_internal_emails: set[str],
) -> bool:
    if not non_consulting_internal_emails:
        return False

    internal_emails = _collect_internal_thread_emails(
        messages,
        recipient_map=recipient_map,
        internal_domains=internal_domains,
    )
    return bool(internal_emails) and internal_emails.issubset(
        non_consulting_internal_emails
    )


def _domain_to_company_label(domain: str) -> str:
    host = domain.split(".", 1)[0].replace("-", " ").replace("_", " ")
    parts = [part for part in host.split() if part]
    return " ".join(part.capitalize() for part in parts) or domain


def _is_internal_email(email: str | None, internal_domains: set[str]) -> bool:
    if not email or "@" not in email:
        return False
    return email.split("@", 1)[1].strip().lower() in internal_domains


def _derive_reply_state(
    messages: list[dict[str, Any]],
    *,
    internal_domains: set[str],
) -> tuple[str, datetime | None, datetime | None]:
    last_external_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None

    for message in messages:
        message_ts = message["message_timestamp"]
        if message["direction"] == "outbound":
            if message_ts and (last_outbound_at is None or message_ts > last_outbound_at):
                last_outbound_at = message_ts
            continue

        if not _is_internal_email(message["sender_email"], internal_domains):
            if (
                message_ts
                and (
                    last_external_inbound_at is None
                    or message_ts > last_external_inbound_at
                )
            ):
                last_external_inbound_at = message_ts

    if last_external_inbound_at is None:
        return "answered", None, last_outbound_at
    if last_outbound_at is None or last_external_inbound_at > last_outbound_at:
        return "unanswered", last_external_inbound_at, last_outbound_at
    return "answered", last_external_inbound_at, last_outbound_at


def _sorted_event_tags(events: list[dict[str, Any]]) -> list[str]:
    event_types = {str(event["event_type"]) for event in events if event["event_type"]}
    return sorted(
        event_types, key=lambda event_type: EVENT_PRIORITY_MAP.get(event_type, 99)
    )


def _pick_primary_event_tag(event_tags: list[str]) -> str | None:
    return event_tags[0] if event_tags else None


def _derive_project_number(
    *,
    linked_project_code: str | None,
    subjects: list[str | None],
) -> str | None:
    if linked_project_code:
        return linked_project_code

    for subject in subjects:
        if not subject:
            continue
        for pattern in PROJECT_NUMBER_PATTERNS:
            match = pattern.search(subject)
            if match:
                return match.group(0).strip()
    return None


def _pick_client_display(
    *,
    linked_client_name: str | None,
    messages: list[dict[str, Any]],
    recipient_map: dict[str, list[dict[str, Any]]],
    internal_domains: set[str],
) -> tuple[str | None, str | None]:
    if linked_client_name:
        for message in messages:
            if message["direction"] == "inbound" and not _is_internal_email(
                message["sender_email"], internal_domains
            ):
                return linked_client_name, message["sender_email"]

        for message in messages:
            for recipient in recipient_map.get(message["id"], []):
                if recipient["is_external"]:
                    return linked_client_name, recipient["email"]

        return linked_client_name, None

    for message in messages:
        if message["direction"] == "inbound" and not _is_internal_email(
            message["sender_email"], internal_domains
        ):
            return message["sender_name"] or message["sender_email"], message["sender_email"]

        for recipient in recipient_map.get(message["id"], []):
            if recipient["is_external"]:
                return recipient["display_name"] or recipient["email"], recipient["email"]

    return None, None


def _derive_client_names(
    *,
    linked_client_name: str | None,
    messages: list[dict[str, Any]],
    recipient_map: dict[str, list[dict[str, Any]]],
    internal_domains: set[str],
) -> list[str]:
    client_names: list[str] = []
    seen: set[str] = set()

    def add_name(candidate: str | None) -> None:
        if not candidate:
            return
        normalized = candidate.strip()
        if not normalized:
            return
        key = normalized.casefold()
        if key in seen:
            return
        seen.add(key)
        client_names.append(normalized)

    if linked_client_name:
        add_name(linked_client_name)

    external_domains: set[str] = set()
    for message in messages:
        sender_email = message["sender_email"]
        if sender_email and "@" in sender_email and not _is_internal_email(
            sender_email, internal_domains
        ):
            external_domains.add(sender_email.split("@", 1)[1].strip().lower())

        for recipient in recipient_map.get(message["id"], []):
            email = recipient["email"]
            if (
                email
                and "@" in email
                and not _is_internal_email(email, internal_domains)
            ):
                external_domains.add(email.split("@", 1)[1].strip().lower())

    for domain in sorted(external_domains):
        add_name(_domain_to_company_label(domain))

    return client_names


def _derive_correspondent(
    *,
    latest_message: dict[str, Any],
    recipient_map: dict[str, list[dict[str, Any]]],
    internal_domains: set[str],
) -> tuple[str | None, str | None, str]:
    if latest_message["direction"] == "inbound":
        return (
            latest_message["sender_name"] or latest_message["sender_email"],
            latest_message["sender_email"],
            "received",
        )

    for recipient in recipient_map.get(latest_message["id"], []):
        email = recipient["email"]
        if email and recipient["is_external"] and not _is_internal_email(email, internal_domains):
            return (
                recipient["display_name"] or email,
                email,
                "sent",
            )

    return (latest_message["sender_name"] or latest_message["sender_email"], latest_message["sender_email"], "sent")


def _load_thread_messages(
    conn: psycopg.Connection[Any], *, thread_record_id: str
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              m.id::text as id,
              m.direction,
              m.sender_email::text as sender_email,
              m.sender_name,
              m.sender_is_internal,
              m.sender_is_external,
              m.subject,
              m.normalized_subject,
              m.body_preview,
              m.body_text,
              m.has_attachments,
              coalesce(m.received_at, m.sent_at, m.created_at_graph) as message_timestamp
            from public.messages m
            where m.thread_record_id = %s
            order by coalesce(m.received_at, m.sent_at, m.created_at_graph) desc nulls last
            """,
            (thread_record_id,),
        )
        return list(cur.fetchall())


def _load_thread_recipients(
    conn: psycopg.Connection[Any], *, thread_record_id: str
) -> dict[str, list[dict[str, Any]]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              mr.message_id::text as message_id,
              mr.recipient_type,
              mr.email::text as email,
              mr.display_name,
              mr.is_internal,
              mr.is_external
            from public.message_recipients mr
            inner join public.messages m on m.id = mr.message_id
            where m.thread_record_id = %s
            order by m.created_at desc
            """,
            (thread_record_id,),
        )
        rows = list(cur.fetchall())

    recipient_map: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        recipient_map.setdefault(str(row["message_id"]), []).append(
            {
                "recipient_type": row["recipient_type"],
                "email": row["email"],
                "display_name": row["display_name"],
                "is_internal": row["is_internal"],
                "is_external": row["is_external"],
            }
        )
    return recipient_map


def _load_thread_events(
    conn: psycopg.Connection[Any], *, thread_record_id: str
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              ce.event_type,
              ce.payload,
              ce.decision_source,
              ce.decision_version,
              ce.confidence,
              coalesce(m.received_at, m.sent_at, m.created_at_graph, ce.created_at) as event_timestamp
            from public.communication_events ce
            left join public.messages m on m.id = ce.message_id
            where ce.thread_record_id = %s
            order by coalesce(m.received_at, m.sent_at, m.created_at_graph, ce.created_at) desc
            """,
            (thread_record_id,),
        )
        return list(cur.fetchall())


def _load_thread_record(
    conn: psycopg.Connection[Any], *, thread_record_id: str
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select
              tr.id::text as id,
              mc.mailbox_address::text as mailbox_address,
              tr.normalized_subject,
              tr.latest_subject,
              tr.current_state,
              tr.current_attention_state,
              tr.latest_correspondence_at,
              tr.client_display_name,
              tr.client_names,
              tr.client_display_email::text as client_display_email,
              tr.correspondent_display_name,
              tr.correspondent_email::text as correspondent_email,
              tr.latest_correspondence_direction,
              tr.no_consulting_staff_attached,
              tr.project_number,
              tr.latest_snippet,
              tr.system_card_header,
              tr.card_header,
              tr.card_header_overridden,
              tr.system_summary,
              tr.summary,
              tr.summary_overridden,
              tr.latest_classification_id::text as latest_classification_id,
              tr.last_classified_at,
              tr.classifier_provider,
              tr.classifier_model,
              tr.classifier_version,
              tr.classifier_overall_confidence,
              tr.system_event_tags,
              tr.event_tags,
              tr.system_primary_event_tag,
              tr.primary_event_tag,
              tr.system_promotion_state,
              tr.promotion_state,
              tr.system_reply_state,
              tr.reply_state,
              tr.system_is_urgent,
              tr.is_urgent,
              tr.review_state,
              tr.first_opened_at,
              tr.last_reviewed_at,
              tr.state_last_changed_at,
              tr.has_human_overrides,
              tr.event_tags_overridden,
              tr.promotion_state_overridden,
              tr.reply_state_overridden,
              tr.urgency_overridden,
              c.name as linked_client_name,
              p.project_code as linked_project_code
            from public.thread_records tr
            inner join public.mailbox_configs mc on mc.id = tr.mailbox_config_id
            left join public.clients c on c.id = tr.client_id
            left join public.projects p on p.id = tr.project_id
            where tr.id = %s
            """,
            (thread_record_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError(f"Thread record {thread_record_id} not found.")
    return row


def _insert_state_history(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    previous_state: dict[str, Any],
    next_state: dict[str, Any],
) -> None:
    history_rows: list[tuple[str, Any, Any]] = []
    for field_name in TRACKED_HISTORY_FIELDS:
        previous_value = _coerce_json_compatible(previous_state.get(field_name))
        next_value = _coerce_json_compatible(next_state.get(field_name))
        if previous_value == next_value:
            continue
        history_rows.append((field_name, previous_value, next_value))

    if not history_rows:
        return

    with conn.cursor() as cur:
        for field_name, old_value, new_value in history_rows:
            cur.execute(
                """
                insert into public.thread_state_history (
                  thread_record_id,
                  actor_type,
                  field_name,
                  old_value,
                  new_value,
                  reason,
                  source
                )
                values (%s, 'system', %s, %s, %s, %s, %s)
                """,
                (
                    thread_record_id,
                    field_name,
                    Jsonb(old_value),
                    Jsonb(new_value),
                    "Thread state recomputed from stored messages and detected events.",
                    "mailbox_sync_refresh",
                ),
            )


def refresh_thread_record(
    conn: psycopg.Connection[Any], *, thread_record_id: str
) -> None:
    previous_state = _load_thread_record(conn, thread_record_id=thread_record_id)
    messages = _load_thread_messages(conn, thread_record_id=thread_record_id)
    if not messages:
        return

    recipient_map = _load_thread_recipients(conn, thread_record_id=thread_record_id)
    events = _load_thread_events(conn, thread_record_id=thread_record_id)
    internal_domains = get_internal_domains(
        conn, mailbox_address=previous_state["mailbox_address"]
    )
    non_consulting_internal_emails = set(get_settings().non_consulting_internal_emails)

    now = utc_now()
    first_message_at = messages[-1]["message_timestamp"]
    last_message_at = messages[0]["message_timestamp"]
    last_inbound_at = next(
        (
            message["message_timestamp"]
            for message in messages
            if message["direction"] == "inbound"
        ),
        None,
    )
    last_outbound_at = next(
        (
            message["message_timestamp"]
            for message in messages
            if message["direction"] == "outbound"
        ),
        None,
    )
    reply_state, last_external_inbound_at, _last_outbound_after_external = _derive_reply_state(
        messages,
        internal_domains=internal_domains,
    )
    has_external_participants = any(
        (
            message["direction"] == "inbound"
            and not _is_internal_email(message["sender_email"], internal_domains)
        )
        or any(
            recipient["is_external"]
            for recipient in recipient_map.get(message["id"], [])
        )
        for message in messages
    )
    no_consulting_staff_attached = _derive_no_consulting_staff_attached(
        messages,
        recipient_map=recipient_map,
        internal_domains=internal_domains,
        non_consulting_internal_emails=non_consulting_internal_emails,
    )

    system_event_tags = _sorted_event_tags(events)
    system_primary_event_tag = _pick_primary_event_tag(system_event_tags)
    system_promotion_state = "promoted" if system_event_tags else "not_promoted"
    system_is_urgent = any(tag in URGENT_EVENT_TYPES for tag in system_event_tags)

    effective_event_tags = (
        list(previous_state["event_tags"] or [])
        if previous_state["event_tags_overridden"]
        else system_event_tags
    )
    effective_primary_event_tag = _pick_primary_event_tag(effective_event_tags)
    effective_promotion_state = (
        previous_state["promotion_state"]
        if previous_state["promotion_state_overridden"]
        else system_promotion_state
    )
    effective_reply_state = (
        previous_state["reply_state"]
        if previous_state["reply_state_overridden"]
        else reply_state
    )
    effective_is_urgent = (
        previous_state["is_urgent"]
        if previous_state["urgency_overridden"]
        else system_is_urgent
    )

    client_display_name, client_display_email = _pick_client_display(
        linked_client_name=previous_state["linked_client_name"],
        messages=messages,
        recipient_map=recipient_map,
        internal_domains=internal_domains,
    )
    client_names = _derive_client_names(
        linked_client_name=previous_state["linked_client_name"],
        messages=messages,
        recipient_map=recipient_map,
        internal_domains=internal_domains,
    )
    latest_message = messages[0]
    (
        correspondent_display_name,
        correspondent_email,
        latest_correspondence_direction,
    ) = _derive_correspondent(
        latest_message=latest_message,
        recipient_map=recipient_map,
        internal_domains=internal_domains,
    )
    latest_snippet = _normalize_whitespace(
        latest_message["body_preview"] or latest_message["body_text"]
    )
    project_number = _derive_project_number(
        linked_project_code=previous_state["linked_project_code"],
        subjects=[message["subject"] for message in messages[:5]]
        + [message["normalized_subject"] for message in messages[:5]],
    )

    first_opened_at = previous_state["first_opened_at"]
    review_state = previous_state["review_state"] or "disregard"
    last_reviewed_at = previous_state["last_reviewed_at"]

    if first_opened_at is None:
        if effective_promotion_state == "promoted":
            review_state = "open"
            first_opened_at = now
            last_reviewed_at = now
        else:
            review_state = "disregard"
    elif review_state not in {"open", "handled", "disregard"}:
        review_state = "open"

    current_attention_state = (
        "action_needed"
        if review_state == "open"
        else "handled"
        if review_state == "handled"
        else "dismissed"
    )
    dashboard_status = "working" if review_state == "open" else "hidden"
    dashboard_reason = (
        effective_primary_event_tag if effective_promotion_state == "promoted" else None
    )
    trigger_count = len(events)
    latest_triggered_at = events[0]["event_timestamp"] if events else None

    next_state = {
        "system_event_tags": system_event_tags,
        "event_tags": effective_event_tags,
        "system_primary_event_tag": system_primary_event_tag,
        "primary_event_tag": effective_primary_event_tag,
        "system_promotion_state": system_promotion_state,
        "promotion_state": effective_promotion_state,
        "system_reply_state": reply_state,
        "reply_state": effective_reply_state,
        "system_is_urgent": system_is_urgent,
        "is_urgent": effective_is_urgent,
        "review_state": review_state,
        "first_opened_at": first_opened_at,
        "latest_correspondence_at": last_message_at,
        "client_display_name": client_display_name,
        "client_names": client_names,
        "project_number": project_number,
        "correspondent_display_name": correspondent_display_name,
        "latest_correspondence_direction": latest_correspondence_direction,
        "no_consulting_staff_attached": no_consulting_staff_attached,
    }
    state_last_changed_at = previous_state["state_last_changed_at"] or now
    if any(
        _coerce_json_compatible(previous_state.get(field_name))
        != _coerce_json_compatible(next_state.get(field_name))
        for field_name in TRACKED_HISTORY_FIELDS
    ):
        state_last_changed_at = now

    _insert_state_history(
        conn,
        thread_record_id=thread_record_id,
        previous_state={
            **previous_state,
            "system_event_tags": list(previous_state["system_event_tags"] or []),
            "event_tags": list(previous_state["event_tags"] or []),
        },
        next_state=next_state,
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            update public.thread_records
            set first_message_at = %s,
                last_message_at = %s,
                last_inbound_at = %s,
                last_outbound_at = %s,
                last_external_inbound_at = %s,
                message_count = %s,
                has_attachments = %s,
                has_external_participants = %s,
                latest_subject = %s,
                latest_correspondence_at = %s,
                client_display_name = %s,
                client_names = %s,
                client_display_email = %s,
                correspondent_display_name = %s,
                correspondent_email = %s,
                latest_correspondence_direction = %s,
                no_consulting_staff_attached = %s,
                project_number = %s,
                latest_snippet = %s,
                system_event_tags = %s,
                event_tags = %s,
                system_primary_event_tag = %s,
                primary_event_tag = %s,
                system_promotion_state = %s,
                promotion_state = %s,
                system_reply_state = %s,
                reply_state = %s,
                system_is_urgent = %s,
                is_urgent = %s,
                review_state = %s,
                first_opened_at = %s,
                last_reviewed_at = %s,
                state_last_changed_at = %s,
                state_decision_source = %s,
                state_decision_version = %s,
                has_human_overrides = %s,
                current_attention_state = %s,
                awaiting_internal_response = %s,
                dashboard_status = %s,
                dashboard_reason = %s,
                dashboard_last_evaluated_at = %s,
                has_trigger = %s,
                trigger_count = %s,
                latest_triggered_at = %s,
                primary_trigger_type = %s,
                trigger_types = %s,
                updated_at = timezone('utc', now())
            where id = %s
            """,
            (
                first_message_at,
                last_message_at,
                last_inbound_at,
                last_outbound_at,
                last_external_inbound_at,
                len(messages),
                any(message["has_attachments"] for message in messages),
                has_external_participants,
                latest_message["subject"],
                last_message_at,
                client_display_name,
                Jsonb(client_names),
                client_display_email,
                correspondent_display_name,
                correspondent_email,
                latest_correspondence_direction,
                no_consulting_staff_attached,
                project_number,
                latest_snippet,
                Jsonb(system_event_tags),
                Jsonb(effective_event_tags),
                system_primary_event_tag,
                effective_primary_event_tag,
                system_promotion_state,
                effective_promotion_state,
                reply_state,
                effective_reply_state,
                system_is_urgent,
                effective_is_urgent,
                review_state,
                first_opened_at,
                last_reviewed_at,
                state_last_changed_at,
                "rule",
                RULE_VERSION,
                bool(previous_state["has_human_overrides"]),
                current_attention_state,
                effective_reply_state == "unanswered",
                dashboard_status,
                dashboard_reason,
                now,
                bool(system_event_tags),
                trigger_count,
                latest_triggered_at,
                system_primary_event_tag,
                Jsonb(system_event_tags),
                thread_record_id,
            ),
        )


def iter_thread_ids_for_classification(
    conn: psycopg.Connection[Any],
    *,
    limit: int,
    only_stale: bool = True,
) -> list[str]:
    conditions = ["has_external_participants = true"]
    if only_stale:
        conditions.append(
            "(last_classified_at is null or latest_correspondence_at is null or last_classified_at < latest_correspondence_at)"
        )

    where_clause = " and ".join(conditions)
    with conn.cursor() as cur:
        cur.execute(
            f"""
            select id::text
            from public.thread_records
            where {where_clause}
            order by latest_correspondence_at desc nulls last
            limit %s
            """,
            (limit,),
        )
        return [str(row["id"]) for row in cur.fetchall()]


def filter_thread_ids_for_classification(
    conn: psycopg.Connection[Any],
    *,
    thread_ids: list[str],
) -> list[str]:
    if not thread_ids:
        return []

    with conn.cursor() as cur:
        cur.execute(
            """
            select id::text
            from public.thread_records
            where has_external_participants = true
              and id = any(%s::uuid[])
            """,
            (thread_ids,),
        )
        visible_thread_ids = {str(row["id"]) for row in cur.fetchall()}

    return [thread_id for thread_id in thread_ids if thread_id in visible_thread_ids]


def load_thread_classification_context(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    max_messages: int,
) -> dict[str, Any]:
    thread = _load_thread_record(conn, thread_record_id=thread_record_id)
    messages = _load_thread_messages(conn, thread_record_id=thread_record_id)[:max_messages]
    recipients = _load_thread_recipients(conn, thread_record_id=thread_record_id)
    events = _load_thread_events(conn, thread_record_id=thread_record_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            select
              m.id::text as message_id,
              a.name,
              a.content_type,
              a.size_bytes
            from public.attachments a
            inner join public.messages m on m.id = a.message_id
            where m.thread_record_id = %s
            order by m.created_at desc, a.created_at desc
            """,
            (thread_record_id,),
        )
        attachment_rows = list(cur.fetchall())

    attachment_map: dict[str, list[dict[str, Any]]] = {}
    for row in attachment_rows:
        attachment_map.setdefault(str(row["message_id"]), []).append(
            {
                "name": row["name"],
                "content_type": row["content_type"],
                "size_bytes": int(row["size_bytes"] or 0),
            }
        )

    serialized_messages: list[dict[str, Any]] = []
    for message in reversed(messages):
        serialized_messages.append(
            {
                "message_id": message["id"],
                "direction": message["direction"],
                "sender_name": message["sender_name"],
                "sender_email": message["sender_email"],
                "subject": message["subject"],
                "body_preview": _normalize_whitespace(message["body_preview"]),
                "body_text": _normalize_whitespace(message["body_text"]),
                "timestamp": message["message_timestamp"].isoformat()
                if message["message_timestamp"]
                else None,
                "recipients": recipient_map_to_serializable(recipients.get(message["id"], [])),
                "attachments": attachment_map.get(message["id"], []),
            }
        )

    return {
        "thread_record_id": thread_record_id,
        "normalized_subject": thread["normalized_subject"],
        "latest_subject": thread["latest_subject"],
        "latest_correspondence_at": thread["latest_correspondence_at"].isoformat()
        if thread["latest_correspondence_at"]
        else None,
        "client_display_name": thread["client_display_name"],
        "client_names": list(thread["client_names"] or []),
        "project_number": thread["project_number"],
        "latest_correspondence_direction": thread["latest_correspondence_direction"],
        "existing_summary": thread["summary"] or thread["system_summary"],
        "existing_effective_event_tags": list(thread["event_tags"] or []),
        "messages": serialized_messages,
        "existing_thread_events": [
            {
                "event_type": row["event_type"],
                "confidence": float(row["confidence"]) if row["confidence"] is not None else None,
                "decision_source": row["decision_source"],
                "decision_version": row["decision_version"],
                "event_timestamp": row["event_timestamp"].isoformat()
                if row["event_timestamp"]
                else None,
            }
            for row in events[:20]
        ],
    }


def recipient_map_to_serializable(
    recipients: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "recipient_type": recipient["recipient_type"],
            "display_name": recipient["display_name"],
            "email": recipient["email"],
            "is_internal": recipient["is_internal"],
            "is_external": recipient["is_external"],
        }
        for recipient in recipients
    ]


def replace_thread_level_communication_events(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    classification_id: str,
    events: list[dict[str, Any]],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            delete from public.communication_events
            where thread_record_id = %s
              and message_id is null
              and decision_source = 'llm'
            """,
            (thread_record_id,),
        )
        for event in events:
            cur.execute(
                """
                insert into public.communication_events (
                  thread_record_id,
                  message_id,
                  event_type,
                  status,
                  payload,
                  decision_source,
                  decision_version,
                  confidence
                )
                values (%s, null, %s, 'detected', %s, 'llm', %s, %s)
                """,
                (
                    thread_record_id,
                    event["event_type"],
                    Jsonb(
                        {
                            "evidence": event["evidence"],
                            "classification_id": classification_id,
                        }
                    ),
                    event["classifier_version"],
                    event["confidence"],
                ),
            )


def persist_thread_classification(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    classifier_provider: str,
    classifier_model: str,
    classifier_version: str,
    prompt_version: str,
    input_checksum: str,
    overall_confidence: float | None,
    card_header: str | None,
    summary: str | None,
    event_tags: list[str],
    primary_event_tag: str | None,
    promotion_state: str,
    reply_state: str,
    is_urgent: bool,
    output_json: dict[str, Any],
    applied_to_thread_state: bool,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.thread_classifications (
              thread_record_id,
              status,
              classifier_provider,
              classifier_model,
              classifier_version,
              prompt_version,
              input_checksum,
              applied_to_thread_state,
              overall_confidence,
              card_header,
              event_tags,
              primary_event_tag,
              promotion_state,
              reply_state,
              is_urgent,
              summary,
              output_json
            )
            values (%s, 'completed', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (
                thread_record_id,
                classifier_provider,
                classifier_model,
                classifier_version,
                prompt_version,
                input_checksum,
                applied_to_thread_state,
                overall_confidence,
                card_header,
                Jsonb(event_tags),
                primary_event_tag,
                promotion_state,
                reply_state,
                is_urgent,
                summary,
                Jsonb(output_json),
            ),
        )
        row = cur.fetchone()
    if row is None:
        raise RuntimeError("Failed to persist thread classification.")
    return str(row["id"])


def persist_failed_thread_classification(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    classifier_provider: str,
    classifier_model: str,
    classifier_version: str,
    prompt_version: str,
    input_checksum: str,
    error_text: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.thread_classifications (
              thread_record_id,
              status,
              classifier_provider,
              classifier_model,
              classifier_version,
              prompt_version,
              input_checksum,
              error_text
            )
            values (%s, 'failed', %s, %s, %s, %s, %s, %s)
            """,
            (
                thread_record_id,
                classifier_provider,
                classifier_model,
                classifier_version,
                prompt_version,
                input_checksum,
                error_text,
            ),
        )


def apply_thread_classification_result(
    conn: psycopg.Connection[Any],
    *,
    thread_record_id: str,
    classification_id: str,
    classifier_provider: str,
    classifier_model: str,
    classifier_version: str,
    overall_confidence: float | None,
    card_header: str | None,
    event_tags: list[str],
    primary_event_tag: str | None,
    promotion_state: str,
    reply_state: str,
    is_urgent: bool,
    summary: str | None,
) -> None:
    previous_state = _load_thread_record(conn, thread_record_id=thread_record_id)

    effective_event_tags = (
        list(previous_state["event_tags"] or [])
        if previous_state["event_tags_overridden"]
        else event_tags
    )
    effective_promotion_state = (
        previous_state["promotion_state"]
        if previous_state["promotion_state_overridden"]
        else promotion_state
    )
    effective_reply_state = (
        previous_state["reply_state"]
        if previous_state["reply_state_overridden"]
        else reply_state
    )
    effective_is_urgent = (
        previous_state["is_urgent"]
        if previous_state["urgency_overridden"]
        else is_urgent
    )
    effective_summary = (
        previous_state["summary"] if previous_state["summary_overridden"] else summary
    )
    effective_card_header = (
        previous_state["card_header"]
        if previous_state["card_header_overridden"]
        else card_header
    )
    review_state = previous_state["review_state"]
    first_opened_at = previous_state["first_opened_at"]
    if previous_state["latest_classification_id"] is None:
        if effective_promotion_state == "promoted":
            review_state = "open"
            first_opened_at = first_opened_at or utc_now()
        else:
            review_state = "disregard"
            first_opened_at = None

    next_state = {
        "system_event_tags": event_tags,
        "event_tags": effective_event_tags,
        "system_primary_event_tag": primary_event_tag,
        "primary_event_tag": effective_event_tags[0] if effective_event_tags else None,
        "system_promotion_state": promotion_state,
        "promotion_state": effective_promotion_state,
        "system_reply_state": reply_state,
        "reply_state": effective_reply_state,
        "system_is_urgent": is_urgent,
        "is_urgent": effective_is_urgent,
        "system_summary": summary,
        "summary": effective_summary,
        "review_state": review_state,
        "first_opened_at": first_opened_at,
        "latest_correspondence_at": previous_state["latest_correspondence_at"],
        "client_display_name": previous_state["client_display_name"],
        "client_names": list(previous_state["client_names"] or []),
        "project_number": previous_state["project_number"],
        "correspondent_display_name": previous_state["correspondent_display_name"],
        "latest_correspondence_direction": previous_state["latest_correspondence_direction"],
        "no_consulting_staff_attached": previous_state["no_consulting_staff_attached"],
        "system_card_header": card_header,
        "card_header": effective_card_header,
    }

    _insert_state_history(
        conn,
        thread_record_id=thread_record_id,
        previous_state={
            **previous_state,
            "system_event_tags": list(previous_state["system_event_tags"] or []),
            "event_tags": list(previous_state["event_tags"] or []),
        },
        next_state=next_state,
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            update public.thread_records
            set system_event_tags = %s,
                event_tags = %s,
                system_primary_event_tag = %s,
                primary_event_tag = %s,
                system_promotion_state = %s,
                promotion_state = %s,
                system_reply_state = %s,
                reply_state = %s,
                system_is_urgent = %s,
                is_urgent = %s,
                system_card_header = %s,
                card_header = %s,
                system_summary = %s,
                summary = %s,
                review_state = %s,
                first_opened_at = %s,
                latest_classification_id = %s,
                last_classified_at = timezone('utc', now()),
                classifier_provider = %s,
                classifier_model = %s,
                classifier_version = %s,
                classifier_overall_confidence = %s,
                state_decision_source = 'llm',
                state_decision_version = %s,
                state_last_changed_at = timezone('utc', now()),
                updated_at = timezone('utc', now())
            where id = %s
            """,
            (
                Jsonb(event_tags),
                Jsonb(effective_event_tags),
                primary_event_tag,
                effective_event_tags[0] if effective_event_tags else None,
                promotion_state,
                effective_promotion_state,
                reply_state,
                effective_reply_state,
                is_urgent,
                effective_is_urgent,
                card_header,
                effective_card_header,
                summary,
                effective_summary,
                review_state,
                first_opened_at,
                classification_id,
                classifier_provider,
                classifier_model,
                classifier_version,
                overall_confidence,
                classifier_version,
                thread_record_id,
            ),
        )
