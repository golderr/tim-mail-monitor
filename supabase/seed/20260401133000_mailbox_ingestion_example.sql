-- Example seed data for local Milestone 2 testing.
-- Replace example values before running against a real environment.

insert into public.users (email, display_name)
values ('ops@yourfirm.com', 'Operations User')
on conflict (email) do update
set display_name = excluded.display_name;

insert into public.internal_domains (domain, description)
values
  ('yourfirm.com', 'Primary internal company domain'),
  ('yourfirm.co', 'Secondary internal company domain')
on conflict (domain) do update
set description = excluded.description,
    is_active = true;

insert into public.mailbox_configs (mailbox_address, display_name, initial_sync_lookback_days)
values ('tim@yourfirm.com', 'Tim Principal Mailbox', 14)
on conflict (mailbox_address) do update
set display_name = excluded.display_name,
    initial_sync_lookback_days = excluded.initial_sync_lookback_days,
    is_active = true,
    polling_enabled = true;

