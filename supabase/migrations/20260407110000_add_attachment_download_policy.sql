alter table public.attachments
  add column if not exists download_eligible boolean not null default false,
  add column if not exists download_policy text not null default 'pending',
  add column if not exists policy_locked_at timestamptz;

create table if not exists public.attachment_download_events (
  id uuid primary key default gen_random_uuid(),
  attachment_id uuid not null references public.attachments(id) on delete cascade,
  message_id uuid not null references public.messages(id) on delete cascade,
  thread_record_id uuid not null references public.thread_records(id) on delete cascade,
  user_email citext,
  status text not null check (status in ('success', 'denied', 'failed')),
  error_text text,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_attachment_download_events_attachment_created
  on public.attachment_download_events (attachment_id, created_at desc);

create index if not exists idx_attachment_download_events_thread_created
  on public.attachment_download_events (thread_record_id, created_at desc);

update public.attachments
set download_eligible = false,
    download_policy = 'historical_hidden_backfill',
    policy_locked_at = timezone('utc', now())
where policy_locked_at is null;
