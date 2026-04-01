create index if not exists idx_mailbox_configs_active
  on public.mailbox_configs (is_active, polling_enabled);

create index if not exists idx_thread_records_mailbox_last_message
  on public.thread_records (mailbox_config_id, last_message_at desc);

create index if not exists idx_messages_thread_record_id
  on public.messages (thread_record_id);

create index if not exists idx_messages_mailbox_received_at
  on public.messages (mailbox_config_id, received_at desc);

create index if not exists idx_messages_mailbox_sent_at
  on public.messages (mailbox_config_id, sent_at desc);

create index if not exists idx_messages_mailbox_conversation_id
  on public.messages (mailbox_config_id, conversation_id);

create index if not exists idx_messages_sender_email
  on public.messages (sender_email);

create index if not exists idx_message_recipients_message_id
  on public.message_recipients (message_id);

create index if not exists idx_attachments_message_id
  on public.attachments (message_id);

create index if not exists idx_sync_runs_mailbox_started_at
  on public.sync_runs (mailbox_config_id, started_at desc);

