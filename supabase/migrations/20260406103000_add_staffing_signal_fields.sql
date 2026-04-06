alter table public.messages
  add column if not exists sender_is_internal boolean not null default false,
  add column if not exists sender_is_external boolean not null default false,
  add column if not exists sender_matched_internal_domain citext;

alter table public.thread_records
  add column if not exists no_consulting_staff_attached boolean not null default false;

update public.messages m
set sender_is_internal = derived.sender_is_internal,
    sender_is_external = derived.sender_is_external,
    sender_matched_internal_domain = derived.sender_matched_internal_domain
from (
  select
    m.id,
    case
      when m.sender_email is null
        or position('@' in m.sender_email::text) = 0
      then false
      when exists (
        select 1
        from public.internal_domains d
        where d.is_active = true
          and lower(d.domain::text) = lower(split_part(m.sender_email::text, '@', 2))
      )
        or lower(split_part(mc.mailbox_address::text, '@', 2))
          = lower(split_part(m.sender_email::text, '@', 2))
      then true
      else false
    end as sender_is_internal,
    case
      when m.sender_email is null
        or position('@' in m.sender_email::text) = 0
      then false
      when exists (
        select 1
        from public.internal_domains d
        where d.is_active = true
          and lower(d.domain::text) = lower(split_part(m.sender_email::text, '@', 2))
      )
        or lower(split_part(mc.mailbox_address::text, '@', 2))
          = lower(split_part(m.sender_email::text, '@', 2))
      then false
      else true
    end as sender_is_external,
    case
      when m.sender_email is null
        or position('@' in m.sender_email::text) = 0
      then null
      when exists (
        select 1
        from public.internal_domains d
        where d.is_active = true
          and lower(d.domain::text) = lower(split_part(m.sender_email::text, '@', 2))
      )
        or lower(split_part(mc.mailbox_address::text, '@', 2))
          = lower(split_part(m.sender_email::text, '@', 2))
      then lower(split_part(m.sender_email::text, '@', 2))::citext
      else null
    end as sender_matched_internal_domain
  from public.messages m
  inner join public.mailbox_configs mc on mc.id = m.mailbox_config_id
) as derived
where m.id = derived.id;
