alter table public.thread_records
  drop constraint if exists thread_records_review_state_check;

alter table public.thread_records
  add constraint thread_records_review_state_check
  check (review_state in ('open', 'handled', 'disregard', 'expired'));

with stale_open_threads as (
  select id
  from public.thread_records
  where review_state = 'open'
    and has_external_participants = true
    and coalesce(
      case
        when last_external_inbound_at is not null
          and latest_triggered_at is not null
          then greatest(last_external_inbound_at, latest_triggered_at)
        else coalesce(last_external_inbound_at, latest_triggered_at)
      end,
      latest_correspondence_at,
      last_message_at,
      first_opened_at
    ) < timezone('utc', now()) - interval '14 days'
)
insert into public.thread_state_history (
  thread_record_id,
  actor_type,
  field_name,
  old_value,
  new_value,
  reason,
  source
)
select
  id,
  'system',
  'review_state',
  '"open"'::jsonb,
  '"expired"'::jsonb,
  'Thread expired after 14 days without new attention-relevant correspondence.',
  'expiration_rule'
from stale_open_threads;

with stale_open_threads as (
  select id
  from public.thread_records
  where review_state = 'open'
    and has_external_participants = true
    and coalesce(
      case
        when last_external_inbound_at is not null
          and latest_triggered_at is not null
          then greatest(last_external_inbound_at, latest_triggered_at)
        else coalesce(last_external_inbound_at, latest_triggered_at)
      end,
      latest_correspondence_at,
      last_message_at,
      first_opened_at
    ) < timezone('utc', now()) - interval '14 days'
)
update public.thread_records tr
set review_state = 'expired',
    last_reviewed_at = timezone('utc', now()),
    state_last_changed_at = timezone('utc', now()),
    state_decision_source = 'rule',
    current_attention_state = 'expired',
    dashboard_status = 'hidden',
    dashboard_reason = 'expired',
    dashboard_last_evaluated_at = timezone('utc', now()),
    updated_at = timezone('utc', now())
from stale_open_threads so
where tr.id = so.id;
