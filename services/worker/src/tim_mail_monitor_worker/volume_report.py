"""Lightweight mailbox traffic estimation using Graph metadata only."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from statistics import mean

from tim_mail_monitor_worker.config import Settings, get_settings
from tim_mail_monitor_worker.db import utc_now
from tim_mail_monitor_worker.graph_client import GraphClient


def estimate_mailbox_volume(
    *,
    mailbox_address: str | None = None,
    days: int = 30,
    max_messages_per_folder: int = 2000,
    settings: Settings | None = None,
) -> dict[str, object]:
    settings = settings or get_settings()
    effective_mailbox = mailbox_address or settings.tim_mailbox_address
    if not effective_mailbox:
        raise RuntimeError("TIM_MAILBOX_ADDRESS is required for volume estimation.")

    since = utc_now() - timedelta(days=days)
    graph_client = GraphClient(settings)
    try:
        inbound_counts: Counter[str] = Counter()
        outbound_counts: Counter[str] = Counter()
        folder_totals: dict[str, int] = {}

        for folder_name in ("Inbox", "SentItems"):
            daily_counter = inbound_counts if folder_name == "Inbox" else outbound_counts
            total = 0
            for message in graph_client.iter_messages(
                mailbox_address=effective_mailbox,
                folder_name=folder_name,
                since=since,
                max_messages=max_messages_per_folder,
                select_fields=(
                    "id",
                    "receivedDateTime",
                    "sentDateTime",
                ),
            ):
                event_at = (
                    message.get("receivedDateTime")
                    if folder_name == "Inbox"
                    else message.get("sentDateTime")
                )
                if not event_at:
                    continue
                total += 1
                daily_counter[event_at[:10]] += 1

            folder_totals[folder_name] = total

        all_days = sorted(set(inbound_counts) | set(outbound_counts))
        combined_daily = [
            inbound_counts.get(day, 0) + outbound_counts.get(day, 0) for day in all_days
        ]
        inbound_daily = [inbound_counts.get(day, 0) for day in all_days]
        outbound_daily = [outbound_counts.get(day, 0) for day in all_days]

        avg_daily_total = mean(combined_daily) if combined_daily else 0.0
        avg_daily_inbound = mean(inbound_daily) if inbound_daily else 0.0
        avg_daily_outbound = mean(outbound_daily) if outbound_daily else 0.0

        six_month_days = 182
        projected_six_month_messages = round(avg_daily_total * six_month_days)

        return {
            "mailbox_address": effective_mailbox,
            "days_sampled": days,
            "folder_totals": folder_totals,
            "daily_breakdown": [
                {
                    "day": day,
                    "inbound": inbound_counts.get(day, 0),
                    "outbound": outbound_counts.get(day, 0),
                    "total": inbound_counts.get(day, 0) + outbound_counts.get(day, 0),
                }
                for day in all_days
            ],
            "average_daily_inbound": round(avg_daily_inbound, 2),
            "average_daily_outbound": round(avg_daily_outbound, 2),
            "average_daily_total": round(avg_daily_total, 2),
            "projected_six_month_messages": projected_six_month_messages,
            "sample_truncated": any(
                total >= max_messages_per_folder for total in folder_totals.values()
            ),
            "max_messages_per_folder": max_messages_per_folder,
        }
    finally:
        graph_client.close()
