alter table public.thread_records
  add column if not exists has_trigger boolean not null default false,
  add column if not exists trigger_count integer not null default 0,
  add column if not exists latest_triggered_at timestamptz,
  add column if not exists primary_trigger_type text,
  add column if not exists trigger_types jsonb not null default '[]'::jsonb;

create index if not exists idx_thread_records_has_trigger_latest
  on public.thread_records (has_trigger, latest_triggered_at desc);

create unique index if not exists idx_communication_events_message_event_type
  on public.communication_events (message_id, event_type)
  where message_id is not null;

