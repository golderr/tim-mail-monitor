import "server-only";

import { query } from "@/lib/server-db";
import { EVENT_TAG_OPTIONS } from "@/lib/thread-flags";

export type DashboardName =
  | "needs_attention"
  | "closed"
  | "not_promoted"
  | "admin";

export type DashboardMetric = {
  needsAttention: number;
  closed: number;
  notPromoted: number;
  urgentOpen: number;
  unansweredOpen: number;
  openPrimaryEventTagCounts: Record<string, number>;
  openNoConsultingStaffCount: number;
  openHasAttachmentCount: number;
  lastSyncStatus: string;
  lastSyncAt: string | null;
  lastSyncMessagesSeen: number;
};

export type DashboardFilters = {
  client?: string;
  projectNumber?: string;
  tags?: string[];
  replyState?: string;
  dateFrom?: string;
  dateTo?: string;
  sort?: "priority" | "latest_desc" | "latest_asc";
  promotionState?: "promoted" | "not_promoted";
  reviewState?: "open" | "handled" | "disregard" | "expired";
  hasOverrides?: "yes" | "no";
  noConsultingStaff?: "yes" | "no";
  hasAttachments?: "yes" | "no";
};

export type ThreadRecipient = {
  recipientType: string;
  email: string;
  displayName: string | null;
  isInternal: boolean;
  isExternal: boolean;
};

export type ThreadAttachment = {
  id: string;
  name: string;
  contentType: string | null;
  sizeBytes: number;
  downloadPath: string;
};

export type ThreadMessage = {
  id: string;
  direction: "sent" | "received";
  subject: string | null;
  bodyText: string | null;
  senderName: string | null;
  senderEmail: string | null;
  senderIsInternal: boolean;
  senderIsExternal: boolean;
  timestamp: string | null;
  recipients: ThreadRecipient[];
  attachments: ThreadAttachment[];
};

export type InternalParticipant = {
  email: string;
  displayName: string | null;
  label: string;
  isOnLatestMessage: boolean;
  lastSeenAt: string | null;
};

export type ThreadStateHistoryEntry = {
  id: string;
  fieldName: string;
  oldValue: string | null;
  newValue: string | null;
  actorType: string;
  actorEmail: string | null;
  source: string | null;
  reason: string | null;
  createdAt: string;
};

export type DashboardThread = {
  id: string;
  clientDisplayName: string | null;
  clientNames: string[];
  externalCorrespondents: string[];
  internalParticipantsCurrent: InternalParticipant[];
  internalParticipantsHistorical: InternalParticipant[];
  title: string;
  cardHeader: string | null;
  eventTags: string[];
  primaryEventTag: string | null;
  isUrgent: boolean;
  noConsultingStaffAttached: boolean;
  hasEligibleAttachments: boolean;
  reviewState: string;
  replyState: string;
  projectNumber: string | null;
  latestCorrespondenceAt: string | null;
  latestCorrespondenceDirection: "sent" | "received" | null;
  summary: string | null;
  promotionState: string;
  hasHumanOverrides: boolean;
  messageCount: number;
  messages: ThreadMessage[];
  stateHistory: ThreadStateHistoryEntry[];
};

function normalizeString(value: string | string[] | undefined) {
  if (!value) {
    return undefined;
  }

  return (Array.isArray(value) ? value[0] : value).trim() || undefined;
}

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((entry): entry is string => typeof entry === "string");
}

function normalizeMultilineText(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  return value.replace(/\r\n?/g, "\n");
}

function normalizeRecipients(value: unknown): ThreadRecipient[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((recipient) => {
    if (!recipient || typeof recipient !== "object") {
      return [];
    }

    const row = recipient as Record<string, unknown>;
    return [
      {
        recipientType:
          typeof row.recipient_type === "string" ? row.recipient_type : "",
        email: typeof row.email === "string" ? row.email : "",
        displayName:
          typeof row.display_name === "string" ? row.display_name : null,
        isInternal: row.is_internal === true,
        isExternal: row.is_external === true,
      },
    ];
  });
}

function normalizeAttachments(value: unknown): ThreadAttachment[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((attachment) => {
    if (!attachment || typeof attachment !== "object") {
      return [];
    }

    const row = attachment as Record<string, unknown>;
    if (typeof row.id !== "string" || typeof row.name !== "string") {
      return [];
    }

    const sizeBytes =
      typeof row.size_bytes === "number"
        ? row.size_bytes
        : typeof row.size_bytes === "string"
          ? Number(row.size_bytes)
          : 0;

    return [
      {
        id: row.id,
        name: row.name,
        contentType:
          typeof row.content_type === "string" ? row.content_type : null,
        sizeBytes: Number.isFinite(sizeBytes) ? sizeBytes : 0,
        downloadPath: `/api/attachments/${row.id}`,
      },
    ];
  });
}

function normalizeMessages(value: Array<Record<string, unknown>>): ThreadMessage[] {
  return value.map((message) => ({
    id: typeof message.id === "string" ? message.id : "",
    direction: message.direction === "received" ? "received" : "sent",
    subject: typeof message.subject === "string" ? message.subject : null,
    bodyText: normalizeMultilineText(message.body_text),
    senderName: typeof message.sender_name === "string" ? message.sender_name : null,
    senderEmail:
      typeof message.sender_email === "string" ? message.sender_email : null,
    senderIsInternal: message.sender_is_internal === true,
    senderIsExternal: message.sender_is_external === true,
    timestamp: typeof message.message_timestamp === "string" ? message.message_timestamp : null,
    recipients: normalizeRecipients(message.recipients),
    attachments: normalizeAttachments(message.attachments),
  }));
}

function normalizeJsonScalar(value: unknown) {
  if (typeof value !== "string") {
    return null;
  }

  try {
    const parsed = JSON.parse(value) as unknown;
    if (parsed === null || parsed === "") {
      return null;
    }
    if (Array.isArray(parsed)) {
      return parsed.join(", ");
    }
    if (typeof parsed === "boolean") {
      return parsed ? "Yes" : "No";
    }
    return String(parsed);
  } catch {
    return value;
  }
}

function parseTagFilters(value: string | string[] | undefined) {
  if (!value) {
    return [];
  }

  const entries = Array.isArray(value) ? value : [value];
  return entries.map((entry) => entry.trim()).filter(Boolean);
}

export function parseDashboardFilters(
  searchParams: Record<string, string | string[] | undefined>,
): DashboardFilters {
  const sort = normalizeString(searchParams.sort) as DashboardFilters["sort"];

  return {
    client: normalizeString(searchParams.client),
    projectNumber: normalizeString(searchParams.projectNumber),
    tags: parseTagFilters(searchParams.tag),
    replyState: normalizeString(searchParams.replyState),
    dateFrom: normalizeString(searchParams.dateFrom),
    dateTo: normalizeString(searchParams.dateTo),
    sort:
      sort === "latest_desc" || sort === "latest_asc" || sort === "priority"
        ? sort
        : "priority",
    promotionState: normalizeString(
      searchParams.promotionState,
    ) as DashboardFilters["promotionState"],
    reviewState: normalizeString(
      searchParams.reviewState,
    ) as DashboardFilters["reviewState"],
    hasOverrides: normalizeString(
      searchParams.hasOverrides,
    ) as DashboardFilters["hasOverrides"],
    noConsultingStaff: normalizeString(
      searchParams.noConsultingStaff,
    ) as DashboardFilters["noConsultingStaff"],
    hasAttachments: normalizeString(
      searchParams.hasAttachments,
    ) as DashboardFilters["hasAttachments"],
  };
}

export function buildReturnToPath(
  pathname: string,
  searchParams: Record<string, string | string[] | undefined>,
) {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(searchParams)) {
    if (!value) {
      continue;
    }

    const entries = Array.isArray(value) ? value : [value];
    for (const entry of entries) {
      if (entry) {
        params.append(key, entry);
      }
    }
  }

  const queryString = params.toString();
  return queryString ? `${pathname}?${queryString}` : pathname;
}

function buildDashboardWhereClause(
  dashboard: DashboardName,
  filters: DashboardFilters,
) {
  const conditions: string[] = ["has_external_participants = true"];
  const params: unknown[] = [];

  switch (dashboard) {
    case "needs_attention":
      conditions.push("review_state = 'open'");
      break;
    case "closed":
      conditions.push("first_opened_at is not null");
      conditions.push("review_state in ('handled', 'disregard', 'expired')");
      break;
    case "not_promoted":
      conditions.push("promotion_state = 'not_promoted'");
      conditions.push("first_opened_at is null");
      break;
    case "admin":
      break;
  }

  if (filters.client) {
    params.push(`%${filters.client}%`);
    conditions.push(
      `(coalesce(client_display_name, '') ilike $${params.length}
        or exists (
          select 1
          from jsonb_array_elements_text(client_names) as client_name
          where client_name ilike $${params.length}
        ))`,
    );
  }

  if (filters.projectNumber) {
    params.push(`%${filters.projectNumber}%`);
    conditions.push(`coalesce(project_number, '') ilike $${params.length}`);
  }

  if (filters.tags && filters.tags.length > 0) {
    const tagConditions: string[] = [];
    for (const tag of filters.tags) {
      params.push(tag);
      tagConditions.push(
        dashboard === "needs_attention"
          ? `primary_event_tag = $${params.length}`
          : `event_tags ? $${params.length}`,
      );
    }
    conditions.push(`(${tagConditions.join(" or ")})`);
  }

  if (filters.replyState) {
    params.push(filters.replyState);
    conditions.push(`reply_state = $${params.length}`);
  }

  if (filters.dateFrom) {
    params.push(filters.dateFrom);
    conditions.push(`latest_correspondence_at >= $${params.length}::timestamptz`);
  }

  if (filters.dateTo) {
    params.push(filters.dateTo);
    conditions.push(
      `latest_correspondence_at < ($${params.length}::date + interval '1 day')`,
    );
  }

  if (dashboard === "admin" && filters.promotionState) {
    params.push(filters.promotionState);
    conditions.push(`promotion_state = $${params.length}`);
  }

  if (dashboard === "admin" && filters.reviewState) {
    params.push(filters.reviewState);
    conditions.push(`review_state = $${params.length}`);
  }

  if (dashboard === "admin" && filters.hasOverrides) {
    conditions.push(
      filters.hasOverrides === "yes"
        ? "has_human_overrides = true"
        : "has_human_overrides = false",
    );
  }

  if (filters.noConsultingStaff) {
    conditions.push(
      filters.noConsultingStaff === "yes"
        ? "no_consulting_staff_attached = true"
        : "no_consulting_staff_attached = false",
    );
  }

  if (filters.hasAttachments) {
    conditions.push(
      filters.hasAttachments === "yes"
        ? `exists (
            select 1
            from public.messages m_filter
            inner join public.attachments a_filter on a_filter.message_id = m_filter.id
            where m_filter.thread_record_id = thread_records.id
              and a_filter.download_eligible = true
              and a_filter.is_inline = false
          )`
        : `not exists (
            select 1
            from public.messages m_filter
            inner join public.attachments a_filter on a_filter.message_id = m_filter.id
            where m_filter.thread_record_id = thread_records.id
              and a_filter.download_eligible = true
              and a_filter.is_inline = false
          )`,
    );
  }

  return {
    params,
    whereClause:
      conditions.length > 0 ? `where ${conditions.join(" and ")}` : "",
  };
}

function buildOrderByClause(filters: DashboardFilters, dashboard: DashboardName) {
  if (filters.sort === "latest_asc") {
    return "order by latest_correspondence_at asc nulls last";
  }

  if (filters.sort === "latest_desc") {
    return "order by latest_correspondence_at desc nulls last";
  }

  if (dashboard === "needs_attention") {
    return "order by is_urgent desc, latest_correspondence_at desc nulls last";
  }

  return "order by latest_correspondence_at desc nulls last";
}

function labelParticipant(displayName: string | null, email: string | null) {
  return displayName || email || "Unknown";
}

function labelInternalParticipant(displayName: string | null, email: string | null) {
  return email || displayName || "Unknown";
}

function deriveParticipants(messages: ThreadMessage[]) {
  const external: string[] = [];
  const externalSeen = new Set<string>();
  const internalParticipants = new Map<string, InternalParticipant>();
  const latestMessageId = messages[0]?.id;

  const add = (list: string[], seen: Set<string>, value: string | null) => {
    if (!value) {
      return;
    }
    const normalized = value.trim();
    if (!normalized) {
      return;
    }
    const key = normalized.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    list.push(normalized);
  };

  const addInternal = (
    message: ThreadMessage,
    displayName: string | null,
    email: string | null,
  ) => {
    const normalizedEmail = email?.trim().toLowerCase();
    const label = labelInternalParticipant(displayName, email);
    const key = normalizedEmail || label.toLowerCase();
    if (!key) {
      return;
    }

    const existing = internalParticipants.get(key);
    if (existing) {
      internalParticipants.set(key, {
        ...existing,
        isOnLatestMessage: existing.isOnLatestMessage || message.id === latestMessageId,
      });
      return;
    }

    internalParticipants.set(key, {
      email: email?.trim() ?? "",
      displayName,
      label,
      isOnLatestMessage: message.id === latestMessageId,
      lastSeenAt: message.timestamp,
    });
  };

  for (const message of messages) {
    if (message.senderIsExternal) {
      add(
        external,
        externalSeen,
        labelParticipant(message.senderName, message.senderEmail),
      );
    }

    if (message.senderIsInternal) {
      addInternal(message, message.senderName, message.senderEmail);
    }

    for (const recipient of message.recipients) {
      const label = labelParticipant(recipient.displayName, recipient.email);
      if (recipient.isExternal) {
        add(external, externalSeen, label);
      }
      if (recipient.isInternal) {
        addInternal(message, recipient.displayName, recipient.email);
      }
    }
  }

  const internalParticipantsCurrent: InternalParticipant[] = [];
  const internalParticipantsHistorical: InternalParticipant[] = [];
  for (const participant of internalParticipants.values()) {
    if (participant.isOnLatestMessage) {
      internalParticipantsCurrent.push(participant);
    } else {
      internalParticipantsHistorical.push(participant);
    }
  }

  return {
    externalCorrespondents: external,
    internalParticipantsCurrent,
    internalParticipantsHistorical,
  };
}

export async function getDashboardMetrics(): Promise<DashboardMetric> {
  const openPrimaryEventTagSelects = EVENT_TAG_OPTIONS.map(
    (option) =>
      `count(*) filter (
          where review_state = 'open'
            and primary_event_tag = '${option.value}'
        )::text as open_${option.value}`,
  ).join(",\n        ");

  const [{ rows: threadRows }, { rows: syncRows }] = await Promise.all([
    query<
      {
      needs_attention: string;
      closed: string;
      not_promoted: string;
      urgent_open: string;
      unanswered_open: string;
      open_no_consulting_staff: string;
      open_has_attachments: string;
    } & Record<string, string | null>
    >(`
      select
        count(*) filter (where review_state = 'open')::text as needs_attention,
        count(*) filter (
          where first_opened_at is not null
            and review_state in ('handled', 'disregard', 'expired')
        )::text as closed,
        count(*) filter (
          where promotion_state = 'not_promoted'
            and first_opened_at is null
        )::text as not_promoted,
        count(*) filter (
          where review_state = 'open'
            and is_urgent = true
        )::text as urgent_open,
        count(*) filter (
          where review_state = 'open'
            and reply_state = 'unanswered'
        )::text as unanswered_open,
        count(*) filter (
          where review_state = 'open'
            and no_consulting_staff_attached = true
        )::text as open_no_consulting_staff,
        count(*) filter (
          where review_state = 'open'
            and exists (
              select 1
              from public.messages m
              inner join public.attachments a on a.message_id = m.id
              where m.thread_record_id = tr.id
                and a.download_eligible = true
                and a.is_inline = false
            )
        )::text as open_has_attachments,
        ${openPrimaryEventTagSelects}
      from public.thread_records tr
      where has_external_participants = true
    `),
    query<{
      status: string;
      completed_at: string | null;
      messages_seen: number;
    }>(`
      select status, completed_at::text, messages_seen
      from public.sync_runs
      order by started_at desc
      limit 1
    `),
  ]);

  const threadRow = threadRows[0];
  const syncRow = syncRows[0];
  const openPrimaryEventTagCounts = Object.fromEntries(
    EVENT_TAG_OPTIONS.map((option) => [
      option.value,
      Number(threadRow?.[`open_${option.value}`] ?? 0),
    ]),
  );

  return {
    needsAttention: Number(threadRow?.needs_attention ?? 0),
    closed: Number(threadRow?.closed ?? 0),
    notPromoted: Number(threadRow?.not_promoted ?? 0),
    urgentOpen: Number(threadRow?.urgent_open ?? 0),
    unansweredOpen: Number(threadRow?.unanswered_open ?? 0),
    openPrimaryEventTagCounts,
    openNoConsultingStaffCount: Number(threadRow?.open_no_consulting_staff ?? 0),
    openHasAttachmentCount: Number(threadRow?.open_has_attachments ?? 0),
    lastSyncStatus: syncRow?.status ?? "unknown",
    lastSyncAt: syncRow?.completed_at ?? null,
    lastSyncMessagesSeen: syncRow?.messages_seen ?? 0,
  };
}

export async function getThreadsForDashboard(
  dashboard: DashboardName,
  filters: DashboardFilters,
  limit = 40,
): Promise<DashboardThread[]> {
  const { params, whereClause } = buildDashboardWhereClause(dashboard, filters);
  const orderByClause = buildOrderByClause(filters, dashboard);
  const limitParam = params.length + 1;

  const { rows } = await query<{
    id: string;
    client_display_name: string | null;
    client_names: unknown;
    title: string | null;
    card_header: string | null;
    event_tags: unknown;
    primary_event_tag: string | null;
    is_urgent: boolean;
    review_state: string;
    reply_state: string;
    project_number: string | null;
    latest_correspondence_at: string | null;
    latest_correspondence_direction: "sent" | "received" | null;
    summary: string | null;
    promotion_state: string;
      has_human_overrides: boolean;
      no_consulting_staff_attached: boolean;
      message_count: number;
    }>(
    `
      select
        id::text,
        client_display_name,
        client_names,
        coalesce(latest_subject, normalized_subject, '(No subject)') as title,
        coalesce(card_header, system_card_header) as card_header,
        event_tags,
        primary_event_tag,
        is_urgent,
        review_state,
        reply_state,
        project_number,
        latest_correspondence_at::text,
        latest_correspondence_direction,
        coalesce(summary, system_summary, latest_snippet) as summary,
        promotion_state,
        has_human_overrides,
        no_consulting_staff_attached,
        message_count
      from public.thread_records
      ${whereClause}
      ${orderByClause}
      limit $${limitParam}
    `,
    [...params, limit],
  );

  if (rows.length === 0) {
    return [];
  }

  const threadIds = rows.map((row) => row.id);
  const { rows: messageRows } = await query<{
    thread_record_id: string;
    id: string;
    direction: "sent" | "received";
    sender_name: string | null;
    sender_email: string | null;
    sender_is_internal: boolean;
    sender_is_external: boolean;
    subject: string | null;
    body_text: string | null;
    message_timestamp: string | null;
    recipients: unknown;
  }>(
    `
      select
        m.thread_record_id::text,
        m.id::text as id,
        case when m.direction = 'outbound' then 'sent' else 'received' end as direction,
        m.sender_name,
        m.sender_email::text,
        m.sender_is_internal,
        m.sender_is_external,
        m.subject,
        coalesce(nullif(m.body_text, ''), m.body_preview) as body_text,
        coalesce(m.received_at, m.sent_at, m.created_at_graph)::text as message_timestamp,
        coalesce(
          (
            select json_agg(
              json_build_object(
                'recipient_type', mr.recipient_type,
                'email', mr.email::text,
                'display_name', mr.display_name,
                'is_internal', mr.is_internal,
                'is_external', mr.is_external
              )
              order by
                case mr.recipient_type
                  when 'to' then 1
                  when 'cc' then 2
                  when 'bcc' then 3
                  else 4
                end,
                mr.email::text
            )
            from public.message_recipients mr
            where mr.message_id = m.id
          ),
          '[]'::json
        ) as recipients
      from public.messages m
      where m.thread_record_id = any($1::uuid[])
      order by coalesce(m.received_at, m.sent_at, m.created_at_graph) desc nulls last
    `,
    [threadIds],
  );

  const messageMap = new Map<string, ThreadMessage[]>();
  const messageIds = messageRows.map((row) => row.id);
  const attachmentMap = new Map<string, ThreadAttachment[]>();
  const stateHistoryMap = new Map<string, ThreadStateHistoryEntry[]>();

  if (messageIds.length > 0) {
    const { rows: attachmentRows } = await query<{
      message_id: string;
      id: string;
      name: string;
      content_type: string | null;
      size_bytes: string;
    }>(
      `
        select
          a.message_id::text as message_id,
          a.id::text,
          a.name,
          a.content_type,
          a.size_bytes::text
        from public.attachments a
        where a.message_id = any($1::uuid[])
          and a.download_eligible = true
          and a.is_inline = false
        order by a.created_at asc, a.name asc
      `,
      [messageIds],
    );

    for (const attachment of attachmentRows) {
      const current = attachmentMap.get(attachment.message_id) ?? [];
      current.push({
        id: attachment.id,
        name: attachment.name,
        contentType: attachment.content_type,
        sizeBytes: Number(attachment.size_bytes || 0),
        downloadPath: `/api/attachments/${attachment.id}`,
      });
      attachmentMap.set(attachment.message_id, current);
    }
  }

  for (const row of messageRows) {
    const message = normalizeMessages([
      {
        id: row.id,
        direction: row.direction,
        sender_name: row.sender_name,
        sender_email: row.sender_email,
        sender_is_internal: row.sender_is_internal,
        sender_is_external: row.sender_is_external,
        subject: row.subject,
        body_text: row.body_text,
        message_timestamp: row.message_timestamp,
        recipients: row.recipients,
        attachments: attachmentMap.get(row.id) ?? [],
      },
    ])[0];
    const current = messageMap.get(row.thread_record_id) ?? [];
    current.push(message);
    messageMap.set(row.thread_record_id, current);
  }

  if (dashboard === "admin") {
    const { rows: historyRows } = await query<{
      thread_record_id: string;
      id: string;
      field_name: string;
      old_value: string | null;
      new_value: string | null;
      actor_type: string;
      actor_email: string | null;
      source: string | null;
      reason: string | null;
      created_at: string;
    }>(
      `
        with ranked_history as (
          select
            h.thread_record_id::text as thread_record_id,
            h.id::text as id,
            h.field_name,
            h.old_value::text as old_value,
            h.new_value::text as new_value,
            h.actor_type,
            u.email::text as actor_email,
            h.source,
            h.reason,
            h.created_at::text,
            row_number() over (
              partition by h.thread_record_id
              order by h.created_at desc
            ) as history_rank
          from public.thread_state_history h
          left join public.users u on u.id = h.actor_user_id
          where h.thread_record_id = any($1::uuid[])
            and h.field_name in (
              'review_state',
              'promotion_state',
              'reply_state',
              'is_urgent',
              'primary_event_tag',
              'event_tags'
            )
        )
        select
          thread_record_id,
          id,
          field_name,
          old_value,
          new_value,
          actor_type,
          actor_email,
          source,
          reason,
          created_at
        from ranked_history
        where history_rank <= 8
        order by created_at desc
      `,
      [threadIds],
    );

    for (const historyRow of historyRows) {
      const current = stateHistoryMap.get(historyRow.thread_record_id) ?? [];
      current.push({
        id: historyRow.id,
        fieldName: historyRow.field_name,
        oldValue: normalizeJsonScalar(historyRow.old_value),
        newValue: normalizeJsonScalar(historyRow.new_value),
        actorType: historyRow.actor_type,
        actorEmail: historyRow.actor_email,
        source: historyRow.source,
        reason: historyRow.reason,
        createdAt: historyRow.created_at,
      });
      stateHistoryMap.set(historyRow.thread_record_id, current);
    }
  }

  return rows.map((row) => {
    const messages = messageMap.get(row.id) ?? [];
    const {
      externalCorrespondents,
      internalParticipantsCurrent,
      internalParticipantsHistorical,
    } =
      deriveParticipants(messages);

    return {
      id: row.id,
      clientDisplayName: row.client_display_name,
      clientNames: normalizeStringArray(row.client_names),
      externalCorrespondents,
      internalParticipantsCurrent,
      internalParticipantsHistorical,
      title: row.title ?? "(No subject)",
      cardHeader: row.card_header,
      eventTags: normalizeStringArray(row.event_tags),
      primaryEventTag: row.primary_event_tag,
      isUrgent: row.is_urgent,
      noConsultingStaffAttached: row.no_consulting_staff_attached,
      hasEligibleAttachments: messages.some(
        (message) => message.attachments.length > 0,
      ),
      reviewState: row.review_state,
      replyState: row.reply_state,
      projectNumber: row.project_number,
      latestCorrespondenceAt: row.latest_correspondence_at,
      latestCorrespondenceDirection: row.latest_correspondence_direction,
      summary: row.summary,
      promotionState: row.promotion_state,
      hasHumanOverrides: row.has_human_overrides,
      messageCount: row.message_count,
      messages: [...messages].reverse(),
      stateHistory: stateHistoryMap.get(row.id) ?? [],
    };
  });
}
