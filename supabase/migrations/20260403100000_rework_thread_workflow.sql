alter table public.thread_records
  add column if not exists system_event_tags jsonb not null default '[]'::jsonb,
  add column if not exists event_tags jsonb not null default '[]'::jsonb,
  add column if not exists system_primary_event_tag text,
  add column if not exists primary_event_tag text,
  add column if not exists system_promotion_state text not null default 'not_promoted'
    check (system_promotion_state in ('promoted', 'not_promoted')),
  add column if not exists promotion_state text not null default 'not_promoted'
    check (promotion_state in ('promoted', 'not_promoted')),
  add column if not exists system_reply_state text not null default 'answered'
    check (system_reply_state in ('unanswered', 'answered', 'partial_answer', 'answered_offline')),
  add column if not exists reply_state text not null default 'answered'
    check (reply_state in ('unanswered', 'answered', 'partial_answer', 'answered_offline')),
  add column if not exists system_is_urgent boolean not null default false,
  add column if not exists is_urgent boolean not null default false,
  add column if not exists review_state text not null default 'disregard'
    check (review_state in ('open', 'handled', 'disregard')),
  add column if not exists first_opened_at timestamptz,
  add column if not exists last_reviewed_at timestamptz,
  add column if not exists latest_correspondence_at timestamptz,
  add column if not exists latest_snippet text,
  add column if not exists client_display_name text,
  add column if not exists client_display_email citext,
  add column if not exists project_number text;

alter table public.communication_events
  add column if not exists decision_source text not null default 'rule',
  add column if not exists decision_version text,
  add column if not exists confidence numeric(5,4),
  add column if not exists is_active boolean not null default true;

create table if not exists public.thread_state_history (
  id uuid primary key default gen_random_uuid(),
  thread_record_id uuid not null references public.thread_records(id) on delete cascade,
  changed_at timestamptz not null default timezone('utc', now()),
  actor_type text not null check (actor_type in ('system', 'user')),
  actor_user_id uuid references public.users(id) on delete set null,
  source text not null,
  field_name text not null,
  old_value jsonb,
  new_value jsonb,
  reason text
);

create index if not exists idx_thread_records_review_state_latest
  on public.thread_records (review_state, latest_correspondence_at desc);

create index if not exists idx_thread_records_promotion_state_latest
  on public.thread_records (promotion_state, latest_correspondence_at desc);

create index if not exists idx_thread_records_reply_state_latest
  on public.thread_records (reply_state, latest_correspondence_at desc);

create index if not exists idx_thread_state_history_thread_changed_at
  on public.thread_state_history (thread_record_id, changed_at desc);

update public.thread_records
set
  system_event_tags = coalesce(trigger_types, '[]'::jsonb),
  event_tags = coalesce(trigger_types, '[]'::jsonb),
  system_primary_event_tag = primary_trigger_type,
  primary_event_tag = primary_trigger_type,
  system_promotion_state = case when coalesce(has_trigger, false) then 'promoted' else 'not_promoted' end,
  promotion_state = case when coalesce(has_trigger, false) then 'promoted' else 'not_promoted' end,
  system_reply_state = case
    when coalesce(awaiting_internal_response, false) then 'unanswered'
    else 'answered'
  end,
  reply_state = case
    when coalesce(awaiting_internal_response, false) then 'unanswered'
    else 'answered'
  end,
  system_is_urgent = coalesce(has_trigger, false),
  is_urgent = coalesce(has_trigger, false),
  review_state = case
    when dashboard_status = 'working' then 'open'
    else 'disregard'
  end,
  first_opened_at = case
    when dashboard_status = 'working' and first_opened_at is null then timezone('utc', now())
    else first_opened_at
  end,
  latest_correspondence_at = coalesce(last_message_at, latest_triggered_at, last_external_inbound_at),
  latest_snippet = coalesce(latest_subject, normalized_subject),
  client_display_name = coalesce(client_display_name, normalized_subject),
  project_number = coalesce(project_number, nullif('', ''));

