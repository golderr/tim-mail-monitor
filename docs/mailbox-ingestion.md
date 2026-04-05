# Mailbox Ingestion Setup

Milestone 2 adds the first real mailbox ingestion path. It is intentionally polling-based and limited to one monitored mailbox.

## Required Environment

Set these values in your local `.env` file:

- `DATABASE_URL`
  - Direct Postgres connection string for your Supabase or local Postgres database
- `MICROSOFT_TENANT_ID`
  - Azure tenant ID for the Microsoft 365 environment
- `MICROSOFT_CLIENT_ID`
  - App registration client ID
- `MICROSOFT_CLIENT_SECRET`
  - Client secret for the app registration
- `TIM_MAILBOX_ADDRESS`
  - The mailbox to poll, for example `tim@yourfirm.com`
- `TIM_MAILBOX_DISPLAY_NAME`
  - Friendly label stored in `mailbox_configs`

Optional tuning values:

- `GRAPH_MAIL_FOLDERS=Inbox,SentItems`
- `GRAPH_MESSAGE_PAGE_SIZE=50`
- `SYNC_LOOKBACK_DAYS=14`
- `SYNC_OVERLAP_MINUTES=5`
- `SYNC_MAX_MESSAGES_PER_FOLDER=200`

## Microsoft Graph Permissions

The worker is written for application credentials and polls a mailbox with Microsoft Graph.

You should grant the app registration mail read permissions that allow reading:

- Inbox messages
- Sent Items messages
- Attachment metadata

The mailbox account must also be allowed for the app in your Microsoft 365 tenant policy.

## Local Database Steps

1. Apply the SQL files in `supabase/migrations/` in timestamp order.
2. Update and run `supabase/seed/20260401133000_mailbox_ingestion_example.sql` if you want starter rows.
3. Verify that `internal_domains` includes your firm domains.

## Local Sync Command

```powershell
cd C:\real_estate_projects\tim-mail-monitor
python -m pip install -e .\services\worker
python -m tim_mail_monitor_worker sync-mailbox --lookback-days 7 --max-messages-per-folder 25
```

The worker will:

1. Ensure a `mailbox_configs` row exists for the monitored mailbox.
2. Create a `sync_runs` row.
3. Poll `Inbox` and `SentItems`.
4. Normalize messages, recipients, and attachments.
5. Upsert `thread_records` and `messages` without duplicating existing Graph message IDs.
6. Refresh thread-level aggregates and mark the sync run complete.

If `--lookback-days` is omitted, the worker uses `mailbox_configs.last_successful_sync_at`
with a small overlap buffer for normal incremental polling.

## Volume Estimate

```powershell
python -m tim_mail_monitor_worker estimate-volume --days 30 --max-messages-per-folder 2000
```

This command uses Graph metadata only, so it is much lighter than a full sync.

## Dashboard Working Set

The worker now marks each thread in `thread_records` with a lightweight
dashboard inclusion state:

- `dashboard_status='working'`
- `dashboard_reason='unanswered_external'` or `recent_external_inbound`
- `awaiting_internal_response=true/false`

This keeps the web UI focused on a staff working set instead of mirroring the
entire mailbox. It is still a heuristic layer, not the final business-trigger
system for deadline changes, scope comments, cancellations, and similar cases.

The current rule-based trigger pass is intentionally narrow and focused on:

- `deadline_change`
- `scope_change`
- `meeting_request`
- `progress_request`
- `cancellation_risk`

You can recompute these from stored messages with:

```powershell
python -m tim_mail_monitor_worker rebuild-triggers
```


## Current Boundaries

- Polling only
- No delta tokens yet
- No webhook subscriptions
- No Teams alerts
- No AI extraction
- No final permissions or RLS
