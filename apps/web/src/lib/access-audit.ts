import "server-only";

import { query } from "@/lib/server-db";

import type { AppRole, AppUser } from "@/lib/auth";

export type AccessEventType = "sign_in" | "sign_out" | "route_access";
export type AccessEventStatus = "success" | "denied" | "failed";

export type UserAccessEvent = {
  id: string;
  userEmail: string | null;
  userRole: AppRole | null;
  eventType: AccessEventType;
  status: AccessEventStatus;
  routePath: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
};

export async function logUserAccessEvent(args: {
  eventType: AccessEventType;
  status: AccessEventStatus;
  routePath?: string | null;
  currentUser?: AppUser | null;
  userEmail?: string | null;
  userRole?: AppRole | null;
  metadata?: Record<string, unknown>;
}) {
  const effectiveEmail = args.currentUser?.email ?? args.userEmail ?? null;
  const effectiveRole = args.currentUser?.role ?? args.userRole ?? null;
  const effectiveUserId = args.currentUser?.id ?? null;

  await query(
    `
      insert into public.user_access_events (
        user_id,
        user_email,
        user_role,
        event_type,
        status,
        route_path,
        metadata
      )
      values ($1::uuid, $2, $3, $4, $5, $6, $7::jsonb)
    `,
    [
      effectiveUserId,
      effectiveEmail,
      effectiveRole,
      args.eventType,
      args.status,
      args.routePath ?? null,
      JSON.stringify(args.metadata ?? {}),
    ],
  );
}

export async function getRecentUserAccessEvents(limit = 40): Promise<UserAccessEvent[]> {
  const { rows } = await query<{
    id: string;
    user_email: string | null;
    user_role: AppRole | null;
    event_type: AccessEventType;
    status: AccessEventStatus;
    route_path: string | null;
    metadata: Record<string, unknown> | null;
    created_at: string;
  }>(
    `
      select
        id::text,
        user_email::text,
        user_role,
        event_type,
        status,
        route_path,
        metadata,
        created_at::text
      from public.user_access_events
      order by created_at desc
      limit $1
    `,
    [limit],
  );

  return rows.map((row) => ({
    id: row.id,
    userEmail: row.user_email,
    userRole: row.user_role,
    eventType: row.event_type,
    status: row.status,
    routePath: row.route_path,
    metadata: row.metadata ?? {},
    createdAt: row.created_at,
  }));
}
