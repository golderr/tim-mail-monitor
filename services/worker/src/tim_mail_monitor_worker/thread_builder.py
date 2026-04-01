"""Thread-key helpers for message grouping."""

from __future__ import annotations

from tim_mail_monitor_worker.models import NormalizedMessage


def build_thread_key(message: NormalizedMessage) -> str:
    if message.conversation_id:
        return f"conversation:{message.conversation_id}"
    if message.internet_message_id:
        return f"internet:{message.internet_message_id}"
    return f"graph:{message.graph_message_id}"
