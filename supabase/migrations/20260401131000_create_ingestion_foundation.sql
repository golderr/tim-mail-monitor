create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email citext not null unique,
  display_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.mailbox_configs (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid references public.users(id) on delete set null,
  mailbox_address citext not null unique,
  display_name text,
  graph_user_id text,
  is_active boolean not null default true,
  polling_enabled boolean not null default true,
  initial_sync_lookback_days integer not null default 30 check (initial_sync_lookback_days > 0),
  last_attempted_sync_at timestamptz,
  last_successful_sync_at timestamptz,
  last_error_text text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.internal_domains (
  id uuid primary key default gen_random_uuid(),
  domain citext not null unique,
  description text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  primary_domain citext unique,
  notes text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references public.clients(id) on delete set null,
  name text not null,
  project_code text unique,
  status text not null default 'active',
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.thread_records (
  id uuid primary key default gen_random_uuid(),
  mailbox_config_id uuid not null references public.mailbox_configs(id) on delete cascade,
  client_id uuid references public.clients(id) on delete set null,
  project_id uuid references public.projects(id) on delete set null,
  thread_key text not null,
  conversation_id text,
  normalized_subject text,
  latest_subject text,
  first_message_at timestamptz,
  last_message_at timestamptz,
  last_inbound_at timestamptz,
  last_outbound_at timestamptz,
  message_count integer not null default 0,
  has_attachments boolean not null default false,
  current_state text not null default 'active',
  current_attention_state text not null default 'unreviewed',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (mailbox_config_id, thread_key)
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  mailbox_config_id uuid not null references public.mailbox_configs(id) on delete cascade,
  thread_record_id uuid not null references public.thread_records(id) on delete cascade,
  graph_message_id text not null,
  internet_message_id text,
  conversation_id text,
  conversation_index text,
  parent_folder_id text,
  folder_name text not null,
  direction text not null check (direction in ('inbound', 'outbound')),
  sender_email citext,
  sender_name text,
  subject text,
  normalized_subject text,
  body_preview text,
  body_text text,
  body_content_type text,
  created_at_graph timestamptz,
  sent_at timestamptz,
  received_at timestamptz,
  last_modified_at_graph timestamptz,
  is_read boolean not null default false,
  is_draft boolean not null default false,
  has_attachments boolean not null default false,
  importance text,
  flag_status text,
  inference_classification text,
  categories jsonb not null default '[]'::jsonb,
  web_link text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (mailbox_config_id, graph_message_id)
);

create table if not exists public.message_recipients (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  recipient_type text not null check (recipient_type in ('to', 'cc', 'bcc', 'reply_to')),
  email citext not null,
  display_name text,
  is_internal boolean not null default false,
  is_external boolean not null default true,
  matched_internal_domain citext,
  created_at timestamptz not null default timezone('utc', now()),
  unique (message_id, recipient_type, email)
);

create table if not exists public.attachments (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages(id) on delete cascade,
  graph_attachment_id text,
  name text not null,
  content_type text,
  size_bytes bigint not null default 0,
  is_inline boolean not null default false,
  content_id text,
  last_modified_at_graph timestamptz,
  storage_mode text not null default 'microsoft_reference' check (storage_mode in ('microsoft_reference', 'downloaded')),
  reference_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  unique (message_id, graph_attachment_id)
);

create table if not exists public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  mailbox_config_id uuid not null references public.mailbox_configs(id) on delete cascade,
  trigger_source text not null default 'manual',
  status text not null check (status in ('running', 'completed', 'failed')),
  folders jsonb not null default '[]'::jsonb,
  checkpoint_start timestamptz,
  checkpoint_end timestamptz,
  messages_seen integer not null default 0,
  messages_inserted integer not null default 0,
  messages_updated integer not null default 0,
  threads_touched integer not null default 0,
  recipients_upserted integer not null default 0,
  attachments_upserted integer not null default 0,
  error_text text,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz
);

create table if not exists public.communication_events (
  id uuid primary key default gen_random_uuid(),
  thread_record_id uuid references public.thread_records(id) on delete cascade,
  message_id uuid references public.messages(id) on delete cascade,
  event_type text not null,
  status text not null default 'stub',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

drop trigger if exists set_users_updated_at on public.users;
create trigger set_users_updated_at
before update on public.users
for each row
execute function public.set_updated_at();

drop trigger if exists set_mailbox_configs_updated_at on public.mailbox_configs;
create trigger set_mailbox_configs_updated_at
before update on public.mailbox_configs
for each row
execute function public.set_updated_at();

drop trigger if exists set_internal_domains_updated_at on public.internal_domains;
create trigger set_internal_domains_updated_at
before update on public.internal_domains
for each row
execute function public.set_updated_at();

drop trigger if exists set_clients_updated_at on public.clients;
create trigger set_clients_updated_at
before update on public.clients
for each row
execute function public.set_updated_at();

drop trigger if exists set_projects_updated_at on public.projects;
create trigger set_projects_updated_at
before update on public.projects
for each row
execute function public.set_updated_at();

drop trigger if exists set_thread_records_updated_at on public.thread_records;
create trigger set_thread_records_updated_at
before update on public.thread_records
for each row
execute function public.set_updated_at();

drop trigger if exists set_messages_updated_at on public.messages;
create trigger set_messages_updated_at
before update on public.messages
for each row
execute function public.set_updated_at();

