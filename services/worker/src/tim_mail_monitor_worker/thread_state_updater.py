"""Apply LLM thread classification results onto thread state."""

from __future__ import annotations

from typing import Any

from tim_mail_monitor_worker.ai_extractor import (
    classify_thread_with_llm,
    is_classifier_configured,
)
from tim_mail_monitor_worker.config import Settings, get_settings
from tim_mail_monitor_worker.db import (
    apply_thread_classification_result,
    filter_thread_ids_for_classification,
    iter_thread_ids_for_classification,
    load_thread_classification_context,
    persist_failed_thread_classification,
    persist_thread_classification,
    replace_thread_level_communication_events,
)


def classify_threads(
    conn: Any,
    *,
    settings: Settings | None = None,
    limit: int = 25,
    only_stale: bool = True,
    thread_ids: list[str] | None = None,
) -> dict[str, int]:
    settings = settings or get_settings()
    if not is_classifier_configured(settings):
        return {"threads_considered": 0, "classifications_applied": 0, "failures": 0}

    if thread_ids is None:
        target_thread_ids = iter_thread_ids_for_classification(
            conn,
            limit=limit,
            only_stale=only_stale,
        )
    else:
        target_thread_ids = filter_thread_ids_for_classification(
            conn,
            thread_ids=thread_ids,
        )

    applied = 0
    failures = 0
    for thread_id in target_thread_ids:
        thread_context = load_thread_classification_context(
            conn,
            thread_record_id=thread_id,
            max_messages=settings.classification_max_messages,
        )
        try:
            decision = classify_thread_with_llm(
                thread_context=thread_context,
                settings=settings,
            )
            classification_id = persist_thread_classification(
                conn,
                thread_record_id=thread_id,
                classifier_provider=decision.provider,
                classifier_model=settings.openai_model,
                classifier_version=settings.classification_prompt_version,
                prompt_version=settings.classification_prompt_version,
                input_checksum=decision.input_checksum,
                overall_confidence=decision.overall_confidence,
                card_header=decision.card_header,
                summary=decision.summary,
                event_tags=decision.event_tags,
                primary_event_tag=decision.primary_event_tag,
                promotion_state=decision.promotion_state,
                reply_state=decision.reply_state,
                is_urgent=decision.is_urgent,
                output_json=decision.raw_output,
                applied_to_thread_state=decision.applied_to_thread_state,
            )
            if decision.applied_to_thread_state:
                apply_thread_classification_result(
                    conn,
                    thread_record_id=thread_id,
                    classification_id=classification_id,
                    classifier_provider=decision.provider,
                    classifier_model=settings.openai_model,
                    classifier_version=settings.classification_prompt_version,
                    overall_confidence=decision.overall_confidence,
                    card_header=decision.card_header,
                    event_tags=decision.event_tags,
                    primary_event_tag=decision.primary_event_tag,
                    promotion_state=decision.promotion_state,
                    reply_state=decision.reply_state,
                    is_urgent=decision.is_urgent,
                    summary=decision.summary,
                )
                replace_thread_level_communication_events(
                    conn,
                    thread_record_id=thread_id,
                    classification_id=classification_id,
                    events=[
                        {
                            "event_type": event["event_type"],
                            "evidence": event["evidence"],
                            "confidence": event["confidence"],
                            "classifier_version": settings.classification_prompt_version,
                        }
                        for event in decision.raw_output.get("event_tags", [])
                        if event["event_type"] in decision.event_tags
                    ],
                )
                applied += 1
        except Exception as exc:
            failures += 1
            persist_failed_thread_classification(
                conn,
                thread_record_id=thread_id,
                classifier_provider="openai",
                classifier_model=settings.openai_model,
                classifier_version=settings.classification_prompt_version,
                prompt_version=settings.classification_prompt_version,
                input_checksum="",
                error_text=str(exc),
            )

    return {
        "threads_considered": len(target_thread_ids),
        "classifications_applied": applied,
        "failures": failures,
    }
