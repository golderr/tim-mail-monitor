import "server-only";

import type { User as SupabaseUser } from "@supabase/supabase-js";
import { redirect } from "next/navigation";

import { logUserAccessEvent } from "@/lib/access-audit";
import { query, withClient } from "@/lib/server-db";
import { createClient as createSupabaseServerClient } from "@/lib/supabase/server";

export type AppRole = "admin" | "lead" | "staff";

export type AppUser = {
  id: string;
  email: string;
  displayName: string | null;
  role: AppRole;
};

type UserRow = {
  id: string;
  email: string;
  display_name: string | null;
  role: AppRole;
  is_active: boolean;
};

function normalizeEmail(value: string | null | undefined) {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  return normalized || null;
}

function mapUserRow(row: UserRow): AppUser {
  return {
    id: row.id,
    email: row.email,
    displayName: row.display_name,
    role: row.role,
  };
}

function getAuthDisplayName(user: SupabaseUser) {
  const metadata = user.user_metadata;
  if (!metadata || typeof metadata !== "object") {
    return null;
  }

  const candidateValues = [
    metadata.full_name,
    metadata.name,
    metadata.display_name,
    metadata.user_display_name,
  ];

  for (const candidate of candidateValues) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }

  return null;
}

async function findActiveUserByEmail(email: string) {
  const { rows } = await query<UserRow>(
    `
      select
        id::text,
        email::text,
        display_name,
        role,
        is_active
      from public.users
      where lower(email::text) = lower($1)
        and is_active = true
      limit 1
    `,
    [email],
  );

  return rows[0] ?? null;
}

export async function syncAuthorizedUser(authUser: SupabaseUser) {
  const email = normalizeEmail(authUser.email);
  if (!email) {
    return null;
  }

  const existingUser = await findActiveUserByEmail(email);
  if (!existingUser) {
    return null;
  }

  await withClient(async (client) => {
    await client.query(
      `
        update public.users
        set auth_user_id = $2::uuid,
            last_login_at = timezone('utc', now()),
            display_name = coalesce(display_name, $3),
            updated_at = timezone('utc', now())
        where id = $1::uuid
      `,
      [existingUser.id, authUser.id, getAuthDisplayName(authUser)],
    );
  });

  return mapUserRow(existingUser);
}

export async function getCurrentUser() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const email = normalizeEmail(user?.email);
  if (!email) {
    return null;
  }

  const appUser = await findActiveUserByEmail(email);
  if (!appUser) {
    await supabase.auth.signOut();
    return null;
  }

  return mapUserRow(appUser);
}

export async function hasSession() {
  return (await getCurrentUser()) !== null;
}

export async function requireSession() {
  const currentUser = await getCurrentUser();
  if (!currentUser) {
    redirect("/login");
  }

  return currentUser;
}

export async function requireAnyRole(
  roles: readonly AppRole[],
  options?: {
    fallbackPath?: string;
    accessPath?: string;
  },
) {
  const currentUser = await requireSession();
  const fallbackPath = options?.fallbackPath ?? "/needs-attention";
  if (!roles.includes(currentUser.role)) {
    await logUserAccessEvent({
      currentUser,
      eventType: "route_access",
      status: "denied",
      routePath: options?.accessPath ?? fallbackPath,
      metadata: {
        required_roles: roles,
      },
    });
    redirect(fallbackPath);
  }

  return currentUser;
}

export async function requireRole(
  role: AppRole,
  options?: {
    fallbackPath?: string;
    accessPath?: string;
  },
) {
  return requireAnyRole([role], options);
}

export async function getSessionIdentity() {
  const currentUser = await getCurrentUser();
  if (!currentUser) {
    return null;
  }

  return {
    email: currentUser.email,
    role: currentUser.role,
  };
}

export async function clearSession() {
  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut();
}
