"""Polling-oriented Outlook mailbox sync orchestration."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from tim_mail_monitor_worker.config import Settings, get_settings
from tim_mail_monitor_worker.event_detector import detect_message_events
from tim_mail_monitor_worker.db import (
    SyncCounters,
    complete_sync_run,
    connect_db,
    create_sync_run,
    ensure_mailbox_config,
    fail_running_sync_runs,
    get_internal_domains,
    refresh_thread_record,
    replace_attachments,
    replace_communication_events,
    replace_message_recipients,
    upsert_message,
    upsert_thread_record,
    utc_now,
)
from tim_mail_monitor_worker.graph_client import GraphClient
from tim_mail_monitor_worker.message_normalizer import normalize_graph_message
from tim_mail_monitor_worker.thread_state_updater import classify_threads
from tim_mail_monitor_worker.thread_builder import build_thread_key


def sync_mailbox(
    *,
    mailbox_address: str | None = None,
    lookback_days: int | None = None,
    max_messages_per_folder: int | None = None,
    settings: Settings | None = None,
) -> dict[str, object]:
    settings = settings or get_settings()
    effective_mailbox = mailbox_address or settings.tim_mailbox_address
    if not effective_mailbox:
        raise RuntimeError("TIM_MAILBOX_ADDRESS is required for mailbox sync.")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required for mailbox sync.")
    if not (
        settings.microsoft_tenant_id
        and settings.microsoft_client_id
        and settings.microsoft_client_secret
    ):
        raise RuntimeError(
            "Microsoft Graph client credentials are required for mailbox sync."
        )

    conn = connect_db(settings)
    graph_client = GraphClient(settings)
    counters = SyncCounters()
    touched_thread_ids: set[str] = set()
    sync_run_id: str | None = None
    mailbox_config_id: str | None = None
    checkpoint_mode = "backfill" if lookback_days is not None else "incremental"
    checkpoint_start = utc_now() - timedelta(days=settings.sync_lookback_days)

    try:
        mailbox_config = ensure_mailbox_config(
            conn,
            mailbox_address=effective_mailbox,
            display_name=settings.tim_mailbox_display_name,
            initial_sync_lookback_days=lookback_days or settings.sync_lookback_days,
        )
        fail_running_sync_runs(
            conn,
            mailbox_config_id=mailbox_config.id,
            reason="Superseded by a newer sync run.",
        )
        if lookback_days is not None:
            checkpoint_start = utc_now() - timedelta(days=lookback_days)
        elif mailbox_config.last_successful_sync_at is not None:
            checkpoint_start = mailbox_config.last_successful_sync_at - timedelta(
                minutes=settings.sync_overlap_minutes
            )
        else:
            checkpoint_mode = "initial_backfill"
            checkpoint_start = utc_now() - timedelta(
                days=mailbox_config.initial_sync_lookback_days
            )
        mailbox_config_id = mailbox_config.id
        sync_run_id = create_sync_run(
            conn,
            mailbox_config_id=mailbox_config.id,
            folders=settings.graph_mail_folders,
            checkpoint_start=checkpoint_start,
        )
        conn.commit()

        internal_domains = get_internal_domains(conn, mailbox_address=effective_mailbox)
        effective_max_messages = max_messages_per_folder or settings.sync_max_messages_per_folder

        for folder_name in settings.graph_mail_folders:
            for raw_message in graph_client.iter_messages(
                mailbox_address=effective_mailbox,
                folder_name=folder_name,
                since=checkpoint_start,
                max_messages=effective_max_messages,
            ):
                counters.messages_seen += 1
                attachments_payload = []
                if raw_message.get("hasAttachments"):
                    attachments_payload = graph_client.get_attachments(
                        mailbox_address=effective_mailbox,
                        message_id=raw_message["id"],
                    )

                normalized_message = normalize_graph_message(
                    raw_message=raw_message,
                    folder_name=folder_name,
                    internal_domains=internal_domains,
                    attachments_payload=attachments_payload,
                )
                normalized_message = replace(
                    normalized_message,
                    thread_key=build_thread_key(normalized_message),
                )
                message_timestamp = (
                    normalized_message.received_at
                    or normalized_message.sent_at
                    or normalized_message.created_at_graph
                )

                thread_record_id = upsert_thread_record(
                    conn,
                    mailbox_config_id=mailbox_config.id,
                    thread_key=normalized_message.thread_key,
                    conversation_id=normalized_message.conversation_id,
                    normalized_subject=normalized_message.normalized_subject,
                    latest_subject=normalized_message.subject,
                    message_timestamp=message_timestamp,
                    direction=normalized_message.direction,
                )
                touched_thread_ids.add(thread_record_id)

                message_id, inserted = upsert_message(
                    conn,
                    mailbox_config_id=mailbox_config.id,
                    thread_record_id=thread_record_id,
                    message=normalized_message,
                )
                if inserted:
                    counters.messages_inserted += 1
                else:
                    counters.messages_updated += 1

                counters.recipients_upserted += replace_message_recipients(
                    conn,
                    message_id=message_id,
                    recipients=normalized_message.recipients,
                )
                counters.attachments_upserted += replace_attachments(
                    conn,
                    message_id=message_id,
                    attachments=normalized_message.attachments,
                )
                replace_communication_events(
                    conn,
                    thread_record_id=thread_record_id,
                    message_id=message_id,
                    events=detect_message_events(
                        normalized_message,
                        internal_domains=internal_domains,
                    ),
                )

        for thread_record_id in touched_thread_ids:
            refresh_thread_record(conn, thread_record_id=thread_record_id)

        classification_summary = classify_threads(
            conn,
            settings=settings,
            limit=len(touched_thread_ids) or 0,
            only_stale=False,
            thread_ids=list(touched_thread_ids),
        )

        counters.threads_touched = len(touched_thread_ids)
        complete_sync_run(
            conn,
            sync_run_id=sync_run_id,
            mailbox_config_id=mailbox_config.id,
            counters=counters,
            checkpoint_end=utc_now(),
        )
        conn.commit()

        return {
            "mailbox_address": effective_mailbox,
            "folders": list(settings.graph_mail_folders),
            "checkpoint_mode": checkpoint_mode,
            "checkpoint_start": checkpoint_start.isoformat(),
            "messages_seen": counters.messages_seen,
            "messages_inserted": counters.messages_inserted,
            "messages_updated": counters.messages_updated,
            "threads_touched": counters.threads_touched,
            "recipients_upserted": counters.recipients_upserted,
            "attachments_upserted": counters.attachments_upserted,
            "sync_run_id": sync_run_id,
            "classifications_applied": classification_summary["classifications_applied"],
            "classification_failures": classification_summary["failures"],
        }
    except Exception as exc:
        conn.rollback()
        if sync_run_id and mailbox_config_id:
            complete_sync_run(
                conn,
                sync_run_id=sync_run_id,
                mailbox_config_id=mailbox_config_id,
                counters=counters,
                checkpoint_end=utc_now(),
                error_text=str(exc),
            )
            conn.commit()
        raise
    finally:
        graph_client.close()
        conn.close()
