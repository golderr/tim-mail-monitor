"""Postgres helpers for mailbox ingestion persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from tim_mail_monitor_worker.config import Settings
from tim_mail_monitor_worker.models import (
    NormalizedAttachment,
    NormalizedMessage,
    NormalizedRecipient,
)


@dataclass(frozen=True)
class MailboxConfigRecord:
    id: str
    mailbox_address: str
    display_name: str | None
    initial_sync_lookback_days: int


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
            returning id, mailbox_address, display_name, initial_sync_lookback_days
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
              %s, %s, %s, %s, %s, %s, %s, %s
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


def refresh_thread_record(
    conn: psycopg.Connection[Any], *, thread_record_id: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            with thread_stats as (
              select
                m.thread_record_id,
                min(coalesce(m.received_at, m.sent_at, m.created_at_graph)) as first_message_at,
                max(coalesce(m.received_at, m.sent_at, m.created_at_graph)) as last_message_at,
                max(case when m.direction = 'inbound' then coalesce(m.received_at, m.sent_at, m.created_at_graph) end) as last_inbound_at,
                max(case when m.direction = 'outbound' then coalesce(m.sent_at, m.received_at, m.created_at_graph) end) as last_outbound_at,
                count(*)::integer as message_count,
                bool_or(m.has_attachments) as has_attachments
              from public.messages m
              where m.thread_record_id = %s
              group by m.thread_record_id
            )
            update public.thread_records tr
            set first_message_at = ts.first_message_at,
                last_message_at = ts.last_message_at,
                last_inbound_at = ts.last_inbound_at,
                last_outbound_at = ts.last_outbound_at,
                message_count = ts.message_count,
                has_attachments = ts.has_attachments,
                updated_at = timezone('utc', now())
            from thread_stats ts
            where tr.id = ts.thread_record_id
            """,
            (thread_record_id,),
        )

