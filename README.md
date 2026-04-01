# Tim Mail Monitor

Milestone 2 foundation for an internal monorepo that monitors Tim's Outlook mailbox, stores message and thread records in Postgres, and provides a staff-facing dashboard shell.

## Monorepo Structure

```text
tim-mail-monitor/
  apps/
    web/
  services/
    worker/
  docs/
  supabase/
    migrations/
    seed/
  .env.example
  README.md
```

## Included In Milestone 2

- `apps/web`: existing minimal internal dashboard shell from Milestone 1.
- `services/worker`: Python worker with Graph polling, normalization, thread reconstruction, and sync-run tracking.
- `supabase/migrations`: first real ingestion schema for mailbox sync storage.
- `supabase/seed`: example local seed data for internal domains and the monitored mailbox.
- `docs`: schema, setup, and ingestion notes.

## Local Development

### Frontend

```powershell
cd C:\real_estate_projects\tim-mail-monitor\apps\web
npm install
npm run dev
```

Open `http://localhost:3000`.

### Worker

```powershell
cd C:\real_estate_projects\tim-mail-monitor
python -m pip install -e .\services\worker
python -m tim_mail_monitor_worker serve
```

Health endpoint: `http://127.0.0.1:8001/health`

CLI health check:

```powershell
python -m tim_mail_monitor_worker healthcheck
```

Mailbox sync:

```powershell
python -m tim_mail_monitor_worker sync-mailbox --lookback-days 7 --max-messages-per-folder 25
```

## Database Setup

Run the SQL migrations in `supabase/migrations/` against your Supabase/Postgres database, then optionally apply the example seed in `supabase/seed/20260401133000_mailbox_ingestion_example.sql` after replacing the placeholder domain and mailbox values.

## Milestone 2 Boundaries

- No webhook subscriptions yet
- No AI extraction or summarization yet
- No Teams alerts yet
- No final role-based permissions or RLS yet
- No final dashboard polish yet

This repo is prepared for those pieces without implementing them prematurely.
