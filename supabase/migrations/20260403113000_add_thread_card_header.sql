alter table public.thread_records
  add column if not exists system_card_header text,
  add column if not exists card_header text,
  add column if not exists card_header_overridden boolean not null default false;
