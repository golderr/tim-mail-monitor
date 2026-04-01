"""Normalized mailbox data structures used by the sync pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NormalizedRecipient:
    recipient_type: str
    email: str
    display_name: str | None
    is_internal: bool
    is_external: bool
    matched_internal_domain: str | None = None


@dataclass(frozen=True)
class NormalizedAttachment:
    graph_attachment_id: str | None
    name: str
    content_type: str | None
    size_bytes: int
    is_inline: bool
    content_id: str | None
    last_modified_at_graph: datetime | None
    storage_mode: str = "microsoft_reference"
    reference_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedMessage:
    graph_message_id: str
    internet_message_id: str | None
    conversation_id: str | None
    conversation_index: str | None
    thread_key: str
    parent_folder_id: str | None
    folder_name: str
    direction: str
    sender_email: str | None
    sender_name: str | None
    subject: str | None
    normalized_subject: str | None
    body_preview: str | None
    body_text: str | None
    body_content_type: str | None
    created_at_graph: datetime | None
    sent_at: datetime | None
    received_at: datetime | None
    last_modified_at_graph: datetime | None
    is_read: bool
    is_draft: bool
    has_attachments: bool
    importance: str | None
    flag_status: str | None
    inference_classification: str | None
    categories: list[str]
    web_link: str | None
    recipients: list[NormalizedRecipient] = field(default_factory=list)
    attachments: list[NormalizedAttachment] = field(default_factory=list)

