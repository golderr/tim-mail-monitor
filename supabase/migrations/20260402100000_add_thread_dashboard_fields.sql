alter table public.thread_records
  add column if not exists has_external_participants boolean not null default false,
  add column if not exists last_external_inbound_at timestamptz,
  add column if not exists awaiting_internal_response boolean not null default false,
  add column if not exists dashboard_status text not null default 'hidden'
    check (dashboard_status in ('hidden', 'working')),
  add column if not exists dashboard_reason text,
  add column if not exists dashboard_last_evaluated_at timestamptz;

create index if not exists idx_thread_records_dashboard_status_last_message
  on public.thread_records (dashboard_status, last_message_at desc);

create index if not exists idx_thread_records_awaiting_internal_response
  on public.thread_records (awaiting_internal_response, last_external_inbound_at desc);

