alter table public.thread_records
  add column if not exists client_names jsonb not null default '[]'::jsonb,
  add column if not exists correspondent_display_name text,
  add column if not exists correspondent_email citext,
  add column if not exists latest_correspondence_direction text
    check (latest_correspondence_direction in ('sent', 'received'));

create index if not exists idx_thread_records_latest_correspondence_direction
  on public.thread_records (latest_correspondence_direction, latest_correspondence_at desc nulls last);
