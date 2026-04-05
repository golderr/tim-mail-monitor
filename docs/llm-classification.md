# LLM Thread Classification

This layer classifies full email threads after ingestion and applies model-derived `system_*` state onto `thread_records` while preserving separate effective state and human overrides.

## What It Does

- assembles thread-level context from recent messages, recipients, attachments, and current thread metadata
- sends that context to OpenAI using a strict structured-output schema
- stores every classification run in `public.thread_classifications`
- applies accepted model decisions back to `thread_records`
- records manual corrections in `public.thread_override_feedback`

## Output Contract

The classifier returns:

- `card_header`
- `summary`
- `event_tags`
- `primary_event_tag`
- `promotion_state`
- `reply_state`
- `is_urgent`
- `overall_confidence`

The model prompt now pushes `summary` to include a lightweight stage judgment when the evidence supports it:

- likely a new project
- likely a project already underway
- unclear from the current thread

Event tags are restricted to:

- `deadline`
- `draft_needed`
- `meeting_request`
- `scope_change`
- `client_materials`
- `status_request`
- `commitment`
- `cancellation_pause`
- `proposal_request`
- `new_project`

## Confidence Policy

- individual event tags are only applied when `confidence >= CLASSIFICATION_EVENT_MIN_CONFIDENCE`
- the overall classification is only applied onto thread state when `overall_confidence >= CLASSIFICATION_OVERALL_MIN_CONFIDENCE`
- low-confidence runs are still persisted in `thread_classifications` for audit, but they are not applied

## Commands

Run thread classification:

```powershell
python -m tim_mail_monitor_worker classify-threads --limit 25
```

Run incremental mailbox sync plus optional classification:

```powershell
python -m tim_mail_monitor_worker sync-mailbox
```

If `OPENAI_API_KEY` is missing, the classifier safely skips work.

## Current Limits

- summary is model-derived, but the rest of the UI still uses deterministic routing based on the effective thread state
- event evidence is persisted, but there is not yet a review UI for classification-by-classification audit
- human overrides are captured, but no automated learning loop has been built on top of them yet
