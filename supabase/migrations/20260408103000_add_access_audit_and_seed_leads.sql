create table if not exists public.user_access_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) on delete set null,
  user_email citext,
  user_role text check (user_role in ('admin', 'lead', 'staff')),
  event_type text not null
    check (event_type in ('sign_in', 'sign_out', 'route_access')),
  status text not null
    check (status in ('success', 'denied', 'failed')),
  route_path text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_user_access_events_created
  on public.user_access_events (created_at desc);

create index if not exists idx_user_access_events_user_created
  on public.user_access_events (user_id, created_at desc);

insert into public.users (email, role, is_active)
values
  ('da@theconcordgroup.com', 'lead', true),
  ('jtw@theconcordgroup.com', 'lead', true),
  ('bkh@theconcordgroup.com', 'lead', true),
  ('jfh@theconcordgroup.com', 'lead', true),
  ('mdr@theconcordgroup.com', 'lead', true)
on conflict (email) do update
set role = excluded.role,
    is_active = excluded.is_active,
    updated_at = timezone('utc', now());
