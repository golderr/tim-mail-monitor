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

