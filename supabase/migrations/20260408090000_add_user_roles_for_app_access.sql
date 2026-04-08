alter table public.users
  add column if not exists role text not null default 'lead'
    check (role in ('admin', 'lead', 'staff')),
  add column if not exists auth_user_id uuid unique references auth.users(id) on delete set null,
  add column if not exists last_login_at timestamptz;

insert into public.users (email, role, is_active)
values ('ng@theconcordgroup.com', 'admin', true)
on conflict (email) do update
set role = 'admin',
    is_active = true,
    updated_at = timezone('utc', now());
