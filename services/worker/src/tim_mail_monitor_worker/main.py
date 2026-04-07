"""CLI entrypoints for serving the worker API and running health checks."""

from __future__ import annotations

import argparse
from pprint import pprint

import uvicorn

from tim_mail_monitor_worker.config import get_settings
from tim_mail_monitor_worker.event_detector import detect_message_events
from tim_mail_monitor_worker.health import get_health_payload
from tim_mail_monitor_worker.mail_sync import sync_mailbox
from tim_mail_monitor_worker.db import (
    connect_db,
    expire_stale_open_threads,
    get_internal_domains,
    iter_messages_for_trigger_backfill,
    refresh_thread_record,
    replace_communication_events,
)
from tim_mail_monitor_worker.thread_state_updater import classify_threads
from tim_mail_monitor_worker.models import (
    NormalizedMessage,
)
from tim_mail_monitor_worker.volume_report import estimate_mailbox_volume


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tim-mail-monitor-worker")
    subcommands = parser.add_subparsers(dest="command")

    serve_parser = subcommands.add_parser("serve", help="Run the worker API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int)

    subcommands.add_parser(
        "healthcheck", help="Print the current worker health payload"
    )
    sync_parser = subcommands.add_parser(
        "sync-mailbox",
        help="Poll Graph and ingest Inbox/SentItems messages into Postgres",
    )
    sync_parser.add_argument(
        "--mailbox",
        help="Override the monitored mailbox address for this run",
    )
    sync_parser.add_argument(
        "--lookback-days",
        type=int,
        help="Only request messages newer than this many days",
    )
    sync_parser.add_argument(
        "--max-messages-per-folder",
        type=int,
        help="Cap the number of messages fetched from each folder for a run",
    )
    volume_parser = subcommands.add_parser(
        "estimate-volume",
        help="Estimate mailbox volume using lightweight Graph metadata reads",
    )
    volume_parser.add_argument(
        "--mailbox",
        help="Override the monitored mailbox address for this report",
    )
    volume_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="How many recent days to sample",
    )
    volume_parser.add_argument(
        "--max-messages-per-folder",
        type=int,
        default=2000,
        help="Safety cap per folder for the estimate",
    )
    subcommands.add_parser(
        "rebuild-triggers",
        help="Recompute lightweight trigger events from stored messages",
    )
    classify_parser = subcommands.add_parser(
        "classify-threads",
        help="Run LLM thread classification against stored thread context",
    )
    classify_parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of threads to classify",
    )
    classify_parser.add_argument(
        "--all",
        action="store_true",
        help="Include threads even if they do not appear stale",
    )

    parser.set_defaults(command="healthcheck")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "serve":
        uvicorn.run(
            "tim_mail_monitor_worker.api:app",
            host=args.host,
            port=args.port or settings.app_port,
            reload=settings.app_env == "development",
        )
        return

    if args.command == "sync-mailbox":
        pprint(
            sync_mailbox(
                mailbox_address=args.mailbox,
                lookback_days=args.lookback_days,
                max_messages_per_folder=args.max_messages_per_folder,
                settings=settings,
            )
        )
        return

    if args.command == "estimate-volume":
        pprint(
            estimate_mailbox_volume(
                mailbox_address=args.mailbox,
                days=args.days,
                max_messages_per_folder=args.max_messages_per_folder,
                settings=settings,
            )
        )
        return

    if args.command == "rebuild-triggers":
        conn = connect_db(settings)
        try:
            with conn.cursor() as cur:
                cur.execute("set statement_timeout = 0")
            internal_domains = get_internal_domains(
                conn, mailbox_address=settings.tim_mailbox_address
            )
            message_rows = iter_messages_for_trigger_backfill(conn)
            touched_thread_ids: set[str] = set()
            event_count = 0
            for row in message_rows:
                sender_email = row["sender_email"]
                sender_domain = (
                    sender_email.split("@", 1)[1].strip().lower()
                    if sender_email and "@" in sender_email
                    else None
                )
                sender_is_internal = bool(sender_domain and sender_domain in internal_domains)
                normalized_message = NormalizedMessage(
                    graph_message_id=row["graph_message_id"],
                    internet_message_id=row["internet_message_id"],
                    conversation_id=row["conversation_id"],
                    conversation_index=row["conversation_index"],
                    thread_key="",
                    parent_folder_id=row["parent_folder_id"],
                    folder_name=row["folder_name"],
                    direction=row["direction"],
                    sender_email=sender_email,
                    sender_name=None,
                    sender_is_internal=sender_is_internal,
                    sender_is_external=bool(sender_domain and not sender_is_internal),
                    sender_matched_internal_domain=(
                        sender_domain if sender_is_internal else None
                    ),
                    subject=row["subject"],
                    normalized_subject=row["normalized_subject"],
                    body_preview=row["body_preview"],
                    body_text=row["body_text"],
                    body_content_type=row["body_content_type"],
                    created_at_graph=row["created_at_graph"],
                    sent_at=row["sent_at"],
                    received_at=row["received_at"],
                    last_modified_at_graph=row["last_modified_at_graph"],
                    is_read=row["is_read"],
                    is_draft=row["is_draft"],
                    has_attachments=row["has_attachments"],
                    importance=row["importance"],
                    flag_status=row["flag_status"],
                    inference_classification=row["inference_classification"],
                    categories=[],
                    web_link=row["web_link"],
                    recipients=[],
                    attachments=[],
                )
                events = detect_message_events(
                    normalized_message,
                    internal_domains=internal_domains,
                )
                event_count += replace_communication_events(
                    conn,
                    thread_record_id=row["thread_record_id"],
                    message_id=row["message_id"],
                    events=events,
                )
                touched_thread_ids.add(row["thread_record_id"])

            for thread_id in touched_thread_ids:
                refresh_thread_record(conn, thread_record_id=thread_id)
            expire_stale_open_threads(conn)
            conn.commit()
            pprint(
                {
                    "messages_processed": len(message_rows),
                    "events_detected": event_count,
                    "threads_refreshed": len(touched_thread_ids),
                }
            )
        finally:
            conn.close()
        return

    if args.command == "classify-threads":
        conn = connect_db(settings)
        try:
            with conn.cursor() as cur:
                cur.execute("set statement_timeout = 0")
            summary = classify_threads(
                conn,
                settings=settings,
                limit=args.limit,
                only_stale=not args.all,
            )
            conn.commit()
            pprint(summary)
        finally:
            conn.close()
        return

    pprint(get_health_payload())
