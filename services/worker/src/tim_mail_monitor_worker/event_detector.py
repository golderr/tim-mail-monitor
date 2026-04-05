"""Rule-based operational event detection aligned to the dashboard taxonomy."""

from __future__ import annotations

from collections.abc import Iterable

from tim_mail_monitor_worker.models import NormalizedMessage, TriggeredEvent


EVENT_LABELS: dict[str, str] = {
    "deadline": "Deadline",
    "draft_needed": "Draft Needed",
    "meeting_request": "Meeting Request",
    "scope_change": "Scope Change",
    "client_materials": "Client Materials",
    "status_request": "Status Request",
    "commitment": "Commitment",
    "cancellation_pause": "Cancellation/Pause",
    "proposal_request": "Proposal Request",
    "new_project": "New Project",
}

URGENT_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "deadline",
        "draft_needed",
        "meeting_request",
        "scope_change",
        "client_materials",
        "status_request",
        "commitment",
        "cancellation_pause",
    }
)

INBOUND_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "deadline",
        "high",
        (
            "deadline",
            "due date",
            "target date",
            "move up",
            "push back",
            "extend",
            "extension",
            "timeline",
            "deliver by",
            "need this by",
        ),
    ),
    (
        "draft_needed",
        "high",
        (
            "draft",
            "redline",
            "before the meeting",
            "before the board meeting",
            "before investor meeting",
            "for the meeting",
            "for review tomorrow",
        ),
    ),
    (
        "meeting_request",
        "high",
        (
            "schedule a call",
            "set up a meeting",
            "review call",
            "hop on a call",
            "meet to discuss",
            "available to meet",
            "can we meet",
            "would you join",
        ),
    ),
    (
        "scope_change",
        "high",
        (
            "scope",
            "out of scope",
            "expand the work",
            "additional work",
            "change the deliverable",
            "revised deliverable",
            "fee change",
            "budget change",
            "proposal revision",
        ),
    ),
    (
        "client_materials",
        "high",
        (
            "attached",
            "see attached",
            "sending over",
            "uploaded",
            "unit mix",
            "site plan",
            "assumptions",
            "materials",
            "files",
        ),
    ),
    (
        "status_request",
        "high",
        (
            "status update",
            "what's the status",
            "whats the status",
            "where do things stand",
            "any update",
            "follow up",
            "eta",
            "checking in",
            "progress",
        ),
    ),
    (
        "cancellation_pause",
        "high",
        (
            "cancel",
            "cancellation",
            "terminate",
            "withdraw",
            "put on hold",
            "pause this",
            "not moving forward",
            "hold off",
        ),
    ),
    (
        "proposal_request",
        "medium",
        (
            "proposal",
            "fee proposal",
            "pricing",
            "send over a proposal",
            "budgetary quote",
            "scope and fee",
        ),
    ),
    (
        "new_project",
        "medium",
        (
            "new project",
            "new assignment",
            "new engagement",
            "new opportunity",
            "looking for help with",
            "can you take this on",
        ),
    ),
)

OUTBOUND_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "commitment",
        "high",
        (
            "i will",
            "we will",
            "i'll send",
            "we'll send",
            "i will send",
            "we will send",
            "i can have this",
            "we can have this",
            "i will get this",
            "we will get this",
            "by tomorrow",
            "by end of day",
            "by friday",
        ),
    ),
)

RULE_VERSION = "rule-v2"


def _matched_terms(searchable: str, terms: Iterable[str]) -> tuple[str, ...]:
    return tuple(term for term in terms if term in searchable)


def detect_message_events(
    message: NormalizedMessage,
    *,
    internal_domains: set[str],
) -> list[TriggeredEvent]:
    searchable_parts = [
        message.subject or "",
        message.normalized_subject or "",
        message.body_preview or "",
        message.body_text or "",
    ]
    searchable = " ".join(searchable_parts).lower()
    sender_domain = (
        message.sender_email.split("@", 1)[1].strip().lower()
        if message.sender_email and "@" in message.sender_email
        else None
    )

    events: list[TriggeredEvent] = []

    if message.direction == "inbound":
        if sender_domain is None or sender_domain in internal_domains:
            return []

        for event_type, severity, terms in INBOUND_RULES:
            matched = _matched_terms(searchable, terms)
            if not matched:
                continue
            if event_type == "client_materials" and not (
                message.has_attachments or "attach" in searchable or "upload" in searchable
            ):
                continue
            events.append(
                TriggeredEvent(
                    event_type=event_type,
                    label=EVENT_LABELS[event_type],
                    severity=severity,
                    matched_terms=matched,
                    confidence=0.55,
                    decision_version=RULE_VERSION,
                )
            )

        return events

    if message.direction == "outbound":
        for event_type, severity, terms in OUTBOUND_RULES:
            matched = _matched_terms(searchable, terms)
            if not matched:
                continue
            events.append(
                TriggeredEvent(
                    event_type=event_type,
                    label=EVENT_LABELS[event_type],
                    severity=severity,
                    matched_terms=matched,
                    confidence=0.45,
                    decision_version=RULE_VERSION,
                )
            )

    return events
