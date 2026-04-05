# Schema Plan

Milestone 1 does not create the full schema yet. This document captures the first-pass structure to guide upcoming migrations.

## Milestone 2 Tables

- `users`
  - Internal staff records for mailbox ownership and future assignment support
- `mailbox_configs`
  - Mailbox-level sync configuration and polling status
- `internal_domains`
  - Domain list used to classify internal vs external recipients
- `clients`
  - External client organizations or individuals
- `projects`
  - Internal project mapping for client threads
- `thread_records`
  - Canonical thread rows keyed by mailbox and conversation/thread key
- `messages`
  - Individual normalized Outlook messages
- `message_recipients`
  - To/cc/bcc/reply-to recipients and internal/external classification
- `attachments`
  - Attachment metadata with Microsoft-reference storage mode
- `sync_runs`
  - Polling run history and counters
- `communication_events`
  - Stub table reserved for later event extraction
- `thread_classifications`
  - Persisted LLM classification runs, model versioning, raw JSON outputs, and confidence
- `thread_override_feedback`
  - Manual corrections against classifier-derived state for future learning/evaluation

## Auth Notes

- Web access will eventually use a real auth provider with staff-only access.
- Roles should be enforced in both application logic and database policies.
- Principal mailbox data should be visible only to approved staff groups.

## Migration Strategy

1. Land the ingestion foundation tables and polling worker.
2. Add first-pass role-backed auth and row-level controls.
3. Add workflow tables for notes, statuses, and assignments.
4. Add digest and notification support.
5. Add AI-derived extraction and event enrichment only after ingestion is stable.
