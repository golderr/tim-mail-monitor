"""CLI entrypoints for serving the worker API and running health checks."""

from __future__ import annotations

import argparse
from pprint import pprint

import uvicorn

from tim_mail_monitor_worker.config import get_settings
from tim_mail_monitor_worker.health import get_health_payload
from tim_mail_monitor_worker.mail_sync import sync_mailbox


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

    pprint(get_health_payload())
