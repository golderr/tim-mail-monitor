"""Thread-level LLM classification for operational dashboards."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from openai import OpenAI
from pydantic import BaseModel, Field

from tim_mail_monitor_worker.config import Settings


class EventTag(str, Enum):
    DEADLINE = "deadline"
    DRAFT_NEEDED = "draft_needed"
    MEETING_REQUEST = "meeting_request"
    SCOPE_CHANGE = "scope_change"
    CLIENT_MATERIALS = "client_materials"
    STATUS_REQUEST = "status_request"
    COMMITMENT = "commitment"
    CANCELLATION_PAUSE = "cancellation_pause"
    PROPOSAL_REQUEST = "proposal_request"
    NEW_PROJECT = "new_project"


class PromotionState(str, Enum):
    PROMOTED = "promoted"
    NOT_PROMOTED = "not_promoted"


class ReplyState(str, Enum):
    UNANSWERED = "unanswered"
    ANSWERED = "answered"
    PARTIAL_ANSWER = "partial_answer"
    ANSWERED_OFFLINE = "answered_offline"


class ClassifiedEvent(BaseModel):
    event_type: EventTag
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(min_length=1, max_length=240)


class ThreadClassificationOutput(BaseModel):
    card_header: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1, max_length=700)
    event_tags: list[ClassifiedEvent] = Field(default_factory=list)
    primary_event_tag: EventTag | None = None
    promotion_state: PromotionState
    promotion_reason: str = Field(min_length=1, max_length=240)
    reply_state: ReplyState
    reply_state_reason: str = Field(min_length=1, max_length=240)
    is_urgent: bool
    urgency_reason: str = Field(min_length=1, max_length=240)
    overall_confidence: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
class ClassificationDecision:
    card_header: str | None
    summary: str | None
    event_tags: list[str]
    primary_event_tag: str | None
    promotion_state: str
    reply_state: str
    is_urgent: bool
    overall_confidence: float | None
    raw_output: dict[str, Any]
    input_checksum: str
    applied_to_thread_state: bool
    provider: str = "openai"


DISPLAY_TIME_ZONE = ZoneInfo("America/Los_Angeles")
WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
WEEKDAY_PATTERN = re.compile(
    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"
)
RELATIVE_DAY_PATTERN = re.compile(r"\b(today|tomorrow|yesterday)\b(?!')", re.IGNORECASE)
EXPLICIT_DATE_SUFFIX_PATTERN = re.compile(
    r"^\s*(?:,?\s*(?:\d{1,2}/\d{1,2}(?:/\d{2,4})?"
    r"|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\.?\s+\d{1,2}(?:,\s*\d{4})?))",
    re.IGNORECASE,
)


SYSTEM_PROMPT = """You classify client email threads for an internal consulting operations dashboard.

Your job is not to summarize the whole inbox. Your job is to determine whether a thread contains operationally meaningful client communication and to emit a strict structured result.

Rules:
- Read the thread as a sequence, not as isolated messages.
- Focus on operationally meaningful changes or asks.
- Only use these event tags: deadline, draft_needed, meeting_request, scope_change, client_materials, status_request, commitment, cancellation_pause, proposal_request, new_project.
- promotion_state must be promoted if the thread contains any valid event tag. Otherwise not_promoted.
- is_urgent should usually be true only when at least one urgent event is present: deadline, draft_needed, meeting_request, scope_change, client_materials, status_request, commitment, cancellation_pause.
- reply_state should describe the current operational state of the thread, not merely the last message direction.
- card_header must be a short, concrete takeaway for the card header. Good examples: "Estimated meeting date: Monday 4/20", "Changed scope: multifamily only", "Project cancellation: client says to hold off", "Client materials sent", "Estimated draft wanted by Monday 4/6".
- card_header must use explicit dates in month/day form when timing is known. Say "Need by Monday 4/6", not "Need by Monday".
- summary must summarize the full thread while emphasizing the most important and latest operational developments.
- summary may use markdown bold for emphasis, but only `**...**` around the most important 2-3 short highlights. Do not use bullets, HTML, or other markdown.
- In the summary, try to explicitly assess whether the thread is likely about a new project, a project already underway, or is still unclear.
- When that assessment is possible, include a short sentence like "Likely for a new project.", "Likely for a project currently underway.", or "Project stage is unclear from the thread so far."
- If the thread strongly implies a meeting date, draft deadline, or other concrete timing, prefer putting that in card_header.
- When referring to weekdays or relative day words like today, tomorrow, or yesterday, convert them into explicit dates using the provided message timestamps and local reference date. Example: "Monday 4/6" or "Friday 4/3".
- Do not guess dates unless the thread provides enough evidence to make a reasonable estimate.
- Prefer complete sentences. Do not end card_header or summary mid-sentence.
- Be conservative. If the thread is ambiguous, lower confidence and avoid inventing event tags.
- Do not mention The Concord Group as a client.
- Ignore automated platform notifications or generic system mail unless the thread also contains a real client request or operational change.
- A plain calendar acceptance, decline, tentative response, join notification, or forwarded invite is not by itself a meeting_request trigger.
- meeting_request should mean substantive coordination or a real ask to meet, review, discuss, or reschedule work.
- Outbound-only follow-up proposals should not be marked unanswered unless a later substantive client ask remains unresolved in the thread.
- Prefer not_promoted over promoted when the evidence is only weak scheduling chatter with no real operational consequence.
"""


def is_classifier_configured(settings: Settings) -> bool:
    return bool(settings.openai_api_key)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=DISPLAY_TIME_ZONE)
    return parsed


def _resolve_reference_local_date(thread_context: dict[str, Any]) -> date | None:
    candidates: list[Any] = [thread_context.get("latest_correspondence_at")]
    candidates.extend(
        message.get("timestamp") for message in reversed(thread_context.get("messages", []))
    )
    for candidate in candidates:
        parsed = _parse_timestamp(candidate)
        if parsed is None:
            continue
        return parsed.astimezone(DISPLAY_TIME_ZONE).date()
    return None


def _format_month_day(value: date) -> str:
    return f"{value.month}/{value.day}"


def _format_weekday_month_day(value: date) -> str:
    return f"{value.strftime('%A')} {_format_month_day(value)}"


def _resolve_weekday_date(
    *,
    reference_date: date,
    weekday_text: str,
    leading_context: str,
) -> date:
    target_index = WEEKDAY_INDEX[weekday_text.lower()]
    current_index = reference_date.weekday()
    next_offset = (target_index - current_index) % 7
    previous_offset = next_offset - 7 if next_offset != 0 else -7
    if re.search(r"\b(last|previous|earlier)\s*$", leading_context, re.IGNORECASE):
        return reference_date + timedelta(days=previous_offset)
    if re.search(r"\bnext\s*$", leading_context, re.IGNORECASE):
        return reference_date + timedelta(days=next_offset or 7)
    return reference_date + timedelta(days=next_offset)


def normalize_classifier_text(
    text: str | None, *, thread_context: dict[str, Any]
) -> str | None:
    if text is None:
        return None

    normalized = re.sub(r"\s+", " ", text.replace("\u200b", " ").strip())
    if not normalized:
        return None

    reference_date = _resolve_reference_local_date(thread_context)
    if reference_date is None:
        return normalized

    normalized = RELATIVE_DAY_PATTERN.sub(
        lambda match: _format_weekday_month_day(
            reference_date
            + timedelta(
                days={
                    "yesterday": -1,
                    "today": 0,
                    "tomorrow": 1,
                }[match.group(1).lower()]
            )
        ),
        normalized,
    )

    def replace_weekday(match: re.Match[str]) -> str:
        trailing = normalized[match.end() :]
        if EXPLICIT_DATE_SUFFIX_PATTERN.match(trailing):
            return match.group(1)
        leading = normalized[max(0, match.start() - 24) : match.start()]
        resolved_date = _resolve_weekday_date(
            reference_date=reference_date,
            weekday_text=match.group(1),
            leading_context=leading,
        )
        return f"{match.group(1)} {_format_month_day(resolved_date)}"

    return WEEKDAY_PATTERN.sub(replace_weekday, normalized)


def build_thread_classification_input(thread_context: dict[str, Any]) -> tuple[str, str]:
    reference_local_date = _resolve_reference_local_date(thread_context)
    prompt_payload = {
        "thread_record_id": thread_context["thread_record_id"],
        "normalized_subject": thread_context.get("normalized_subject"),
        "latest_subject": thread_context.get("latest_subject"),
        "client_names": thread_context.get("client_names", []),
        "project_number": thread_context.get("project_number"),
        "latest_correspondence_at": thread_context.get("latest_correspondence_at"),
        "latest_correspondence_direction": thread_context.get(
            "latest_correspondence_direction"
        ),
        "reference_timezone": "America/Los_Angeles",
        "reference_local_date": (
            reference_local_date.isoformat() if reference_local_date is not None else None
        ),
        "existing_summary": thread_context.get("existing_summary"),
        "existing_effective_event_tags": thread_context.get(
            "existing_effective_event_tags", []
        ),
        "messages": thread_context.get("messages", []),
    }
    serialized = json.dumps(prompt_payload, ensure_ascii=True, separators=(",", ":"))
    checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return serialized, checksum


def classify_thread_with_llm(
    *,
    thread_context: dict[str, Any],
    settings: Settings,
) -> ClassificationDecision:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for thread classification.")

    serialized_input, input_checksum = build_thread_classification_input(thread_context)
    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    response = client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Classify this email thread for operational dashboard use.\n"
                    "Return only the required schema.\n"
                    f"{serialized_input}"
                ),
            },
        ],
        text_format=ThreadClassificationOutput,
        reasoning={"effort": settings.openai_reasoning_effort},
        text={"verbosity": settings.openai_text_verbosity},
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed classification output.")

    normalized_card_header = normalize_classifier_text(
        parsed.card_header,
        thread_context=thread_context,
    )
    normalized_summary = normalize_classifier_text(
        parsed.summary,
        thread_context=thread_context,
    )
    filtered_events = [
        event
        for event in parsed.event_tags
        if event.confidence >= settings.classification_event_min_confidence
    ]
    filtered_event_tags = [event.event_type.value for event in filtered_events]
    primary_event_tag = (
        parsed.primary_event_tag.value
        if parsed.primary_event_tag is not None
        and parsed.primary_event_tag.value in filtered_event_tags
        else filtered_event_tags[0]
        if filtered_event_tags
        else None
    )
    applied_to_thread_state = (
        parsed.overall_confidence >= settings.classification_overall_min_confidence
    )
    normalized_output = parsed.model_dump(mode="json")
    normalized_output["card_header"] = normalized_card_header
    normalized_output["summary"] = normalized_summary

    return ClassificationDecision(
        card_header=normalized_card_header,
        summary=normalized_summary,
        event_tags=filtered_event_tags,
        primary_event_tag=primary_event_tag,
        promotion_state=(
            PromotionState.PROMOTED.value
            if filtered_event_tags
            else PromotionState.NOT_PROMOTED.value
        ),
        reply_state=parsed.reply_state.value,
        is_urgent=parsed.is_urgent,
        overall_confidence=parsed.overall_confidence,
        raw_output=normalized_output,
        input_checksum=input_checksum,
        applied_to_thread_state=applied_to_thread_state,
    )
