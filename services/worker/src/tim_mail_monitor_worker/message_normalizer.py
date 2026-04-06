"""Normalize Microsoft Graph messages into database-ready records."""

from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import Any

from tim_mail_monitor_worker.models import (
    NormalizedAttachment,
    NormalizedMessage,
    NormalizedRecipient,
)


SUBJECT_PREFIX_RE = re.compile(r"^\s*((re|fw|fwd)\s*:\s*)+", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _strip_html(value: str | None) -> str | None:
    if not value:
        return value

    return unescape(HTML_TAG_RE.sub(" ", value)).strip()


def normalize_subject(subject: str | None) -> str | None:
    if not subject:
        return None

    normalized = SUBJECT_PREFIX_RE.sub("", subject).strip()
    return normalized or subject.strip()


def _extract_email_address(payload: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not payload:
        return None, None

    email_address = payload.get("emailAddress") or {}
    address = email_address.get("address")
    name = email_address.get("name")
    return (address.lower() if isinstance(address, str) else None, name)


def _classify_email(
    email: str | None, internal_domains: set[str]
) -> tuple[bool, bool, str | None]:
    if not email or "@" not in email:
        return False, False, None

    domain = email.split("@", 1)[1].strip().lower()
    is_internal = domain in internal_domains
    return is_internal, not is_internal, domain if is_internal else None


def _normalize_recipients(
    recipient_type: str,
    recipients: list[dict[str, Any]],
    internal_domains: set[str],
) -> list[NormalizedRecipient]:
    normalized: list[NormalizedRecipient] = []
    seen: set[tuple[str, str]] = set()

    for recipient in recipients:
        email, display_name = _extract_email_address(recipient)
        if not email:
            continue

        dedupe_key = (recipient_type, email)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        is_internal, is_external, matched_domain = _classify_email(
            email, internal_domains
        )
        normalized.append(
            NormalizedRecipient(
                recipient_type=recipient_type,
                email=email,
                display_name=display_name,
                is_internal=is_internal,
                is_external=is_external,
                matched_internal_domain=matched_domain,
            )
        )

    return normalized


def normalize_graph_message(
    *,
    raw_message: dict[str, Any],
    folder_name: str,
    internal_domains: set[str],
    attachments_payload: list[dict[str, Any]],
) -> NormalizedMessage:
    sender_email, sender_name = _extract_email_address(raw_message.get("from"))
    (
        sender_is_internal,
        sender_is_external,
        sender_matched_internal_domain,
    ) = _classify_email(sender_email, internal_domains)
    body = raw_message.get("body") or {}
    body_content = body.get("content")
    body_content_type = body.get("contentType")
    body_text = (
        _strip_html(body_content)
        if str(body_content_type).lower() == "html"
        else body_content
    )

    recipients = (
        _normalize_recipients("to", raw_message.get("toRecipients") or [], internal_domains)
        + _normalize_recipients("cc", raw_message.get("ccRecipients") or [], internal_domains)
        + _normalize_recipients("bcc", raw_message.get("bccRecipients") or [], internal_domains)
        + _normalize_recipients("reply_to", raw_message.get("replyTo") or [], internal_domains)
    )

    normalized_attachments = [
        NormalizedAttachment(
            graph_attachment_id=attachment.get("id"),
            name=attachment.get("name") or "unnamed",
            content_type=attachment.get("contentType"),
            size_bytes=int(attachment.get("size") or 0),
            is_inline=bool(attachment.get("isInline")),
            content_id=attachment.get("contentId"),
            last_modified_at_graph=_parse_datetime(
                attachment.get("lastModifiedDateTime")
            ),
            reference_payload={
                "odata_type": attachment.get("@odata.type"),
                "graph_attachment_id": attachment.get("id"),
                "name": attachment.get("name"),
            },
        )
        for attachment in attachments_payload
    ]

    return NormalizedMessage(
        graph_message_id=raw_message["id"],
        internet_message_id=raw_message.get("internetMessageId"),
        conversation_id=raw_message.get("conversationId"),
        conversation_index=raw_message.get("conversationIndex"),
        thread_key="",
        parent_folder_id=raw_message.get("parentFolderId"),
        folder_name=folder_name,
        direction="outbound" if folder_name == "SentItems" else "inbound",
        sender_email=sender_email,
        sender_name=sender_name,
        sender_is_internal=sender_is_internal,
        sender_is_external=sender_is_external,
        sender_matched_internal_domain=sender_matched_internal_domain,
        subject=raw_message.get("subject"),
        normalized_subject=normalize_subject(raw_message.get("subject")),
        body_preview=raw_message.get("bodyPreview"),
        body_text=body_text,
        body_content_type=body_content_type,
        created_at_graph=_parse_datetime(raw_message.get("createdDateTime")),
        sent_at=_parse_datetime(raw_message.get("sentDateTime")),
        received_at=_parse_datetime(raw_message.get("receivedDateTime")),
        last_modified_at_graph=_parse_datetime(raw_message.get("lastModifiedDateTime")),
        is_read=bool(raw_message.get("isRead")),
        is_draft=bool(raw_message.get("isDraft")),
        has_attachments=bool(raw_message.get("hasAttachments")),
        importance=raw_message.get("importance"),
        flag_status=(raw_message.get("flag") or {}).get("flagStatus"),
        inference_classification=raw_message.get("inferenceClassification"),
        categories=list(raw_message.get("categories") or []),
        web_link=raw_message.get("webLink"),
        recipients=recipients,
        attachments=normalized_attachments,
    )
