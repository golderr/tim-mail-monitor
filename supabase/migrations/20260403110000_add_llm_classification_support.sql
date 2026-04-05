create table if not exists public.thread_classifications (
  id uuid primary key default gen_random_uuid(),
  thread_record_id uuid not null references public.thread_records(id) on delete cascade,
  status text not null default 'completed'
    check (status in ('completed', 'failed', 'skipped')),
  classifier_provider text not null default 'openai',
  classifier_model text,
  classifier_version text,
  prompt_version text,
  input_checksum text,
  applied_to_thread_state boolean not null default false,
  overall_confidence numeric(5,4),
  event_tags jsonb not null default '[]'::jsonb,
  primary_event_tag text,
  promotion_state text
    check (promotion_state in ('promoted', 'not_promoted')),
  reply_state text
    check (reply_state in ('unanswered', 'answered', 'partial_answer', 'answered_offline')),
  is_urgent boolean,
  summary text,
  output_json jsonb not null default '{}'::jsonb,
  error_text text,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.thread_override_feedback (
  id uuid primary key default gen_random_uuid(),
  thread_record_id uuid not null references public.thread_records(id) on delete cascade,
  thread_classification_id uuid references public.thread_classifications(id) on delete set null,
  actor_user_id uuid references public.users(id) on delete set null,
  field_name text not null,
  system_value jsonb,
  effective_value jsonb,
  note text,
  created_at timestamptz not null default timezone('utc', now())
);

alter table public.thread_records
  add column if not exists system_summary text,
  add column if not exists summary text,
  add column if not exists summary_overridden boolean not null default false,
  add column if not exists latest_classification_id uuid references public.thread_classifications(id) on delete set null,
  add column if not exists last_classified_at timestamptz,
  add column if not exists classifier_provider text,
  add column if not exists classifier_model text,
  add column if not exists classifier_version text,
  add column if not exists classifier_overall_confidence numeric(5,4);

create index if not exists idx_thread_classifications_thread_created
  on public.thread_classifications (thread_record_id, created_at desc);

create index if not exists idx_thread_classifications_status_created
  on public.thread_classifications (status, created_at desc);

create index if not exists idx_thread_override_feedback_thread_created
  on public.thread_override_feedback (thread_record_id, created_at desc);
