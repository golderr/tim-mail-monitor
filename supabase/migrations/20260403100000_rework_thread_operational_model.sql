alter table public.thread_records
  add column if not exists latest_correspondence_at timestamptz,
  add column if not exists client_display_name text,
  add column if not exists client_display_email citext,
  add column if not exists project_number text,
  add column if not exists latest_snippet text,
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
  add column if not exists state_last_changed_at timestamptz,
  add column if not exists state_decision_source text not null default 'rule',
  add column if not exists state_decision_version text,
  add column if not exists has_human_overrides boolean not null default false,
  add column if not exists event_tags_overridden boolean not null default false,
  add column if not exists promotion_state_overridden boolean not null default false,
  add column if not exists reply_state_overridden boolean not null default false,
  add column if not exists urgency_overridden boolean not null default false;

alter table public.communication_events
  add column if not exists decision_source text not null default 'rule',
  add column if not exists decision_version text,
  add column if not exists confidence numeric(5,4);

create table if not exists public.thread_state_history (
  id uuid primary key default gen_random_uuid(),
  thread_record_id uuid not null references public.thread_records(id) on delete cascade,
  actor_type text not null check (actor_type in ('system', 'user')),
  actor_user_id uuid references public.users(id) on delete set null,
  field_name text not null,
  old_value jsonb,
  new_value jsonb,
  reason text,
  source text,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_thread_records_review_state_latest_correspondence
  on public.thread_records (review_state, latest_correspondence_at desc nulls last);

create index if not exists idx_thread_records_not_promoted
  on public.thread_records (promotion_state, first_opened_at, latest_correspondence_at desc nulls last);

create index if not exists idx_thread_records_urgent_latest_correspondence
  on public.thread_records (is_urgent, latest_correspondence_at desc nulls last);

create index if not exists idx_thread_records_project_number
  on public.thread_records (project_number);

create index if not exists idx_thread_records_client_display_name
  on public.thread_records (client_display_name);

create index if not exists idx_thread_records_event_tags
  on public.thread_records using gin (event_tags);

create index if not exists idx_thread_state_history_thread_created
  on public.thread_state_history (thread_record_id, created_at desc);
