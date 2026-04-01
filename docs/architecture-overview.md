# Architecture Overview

## Current Scope

The current repo establishes the local development workflow for three main areas:

- `apps/web`: internal dashboard frontend
- `services/worker`: Python mailbox sync worker with Graph polling
- `supabase`: database migrations and seed assets for ingestion

## Intended Flow Later

1. Worker polls Microsoft Graph for Tim's mailbox.
2. Messages are normalized, grouped into threads, and written into Supabase.
3. Web app reads role-scoped data and exposes staff workflows.
4. Alerts and digests are sent to Microsoft Teams and other internal channels.
5. AI enrichment runs only after ingestion and permissions are in place.

## Current Decisions

- Keep the web app simple and server-rendered where possible.
- Use a minimal placeholder auth gate in the UI so page structure can be built without committing to the final provider yet.
- Use a Python package layout for the worker so it can grow into scheduled jobs, API endpoints, and CLI tasks.
- Start with polling against Inbox and Sent Items before adding delta or webhook complexity.
- Store normalized messages, recipients, attachments, and thread aggregates directly in Postgres first.
