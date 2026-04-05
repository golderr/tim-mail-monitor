alter table public.thread_classifications
  add column if not exists card_header text;
