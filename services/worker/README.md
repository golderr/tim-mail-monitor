# Worker Service

Python worker for the Tim Mail Monitor ingestion foundation.

## Included In Milestone 2

- Postgres-backed mailbox ingestion pipeline
- Microsoft Graph polling scaffold for one mailbox
- Inbox and Sent Items sync
- Thread reconstruction and sync-run tracking
- FastAPI `/health` endpoint

## Run

```powershell
cd C:\real_estate_projects\tim-mail-monitor
python -m pip install -e .\services\worker
python -m tim_mail_monitor_worker serve
```

## Test Sync

```powershell
python -m tim_mail_monitor_worker sync-mailbox --lookback-days 7 --max-messages-per-folder 25
```

Normal polling can now omit `--lookback-days`; the worker uses the mailbox's
last successful sync timestamp plus a small overlap window.

## Volume Estimate

```powershell
python -m tim_mail_monitor_worker estimate-volume --days 30 --max-messages-per-folder 2000
```

The worker also populates a lightweight thread working set on `thread_records`
using `dashboard_status`, `dashboard_reason`, and `awaiting_internal_response`.
This is intentionally heuristic, not a final semantic trigger engine.

## Trigger Rebuild

```powershell
python -m tim_mail_monitor_worker rebuild-triggers
```

This recomputes lightweight trigger events from already stored messages.
