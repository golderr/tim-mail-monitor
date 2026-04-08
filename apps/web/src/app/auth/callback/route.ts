import { NextResponse } from "next/server";

import { logUserAccessEvent } from "@/lib/access-audit";
import { clearSession, syncAuthorizedUser, type AppRole } from "@/lib/auth";
import { createClient as createSupabaseServerClient } from "@/lib/supabase/server";

const LEAD_ALLOWED_PATHS = new Set([
  "/",
  "/dashboard",
  "/needs-attention",
  "/closed",
]);

function normalizeNextPath(value: string | null) {
  if (!value || !value.startsWith("/")) {
    return "/needs-attention";
  }

  return value;
}

function getPostLoginPath(role: AppRole, requestedPath: string) {
  if (role === "admin") {
    return requestedPath;
  }

  return LEAD_ALLOWED_PATHS.has(requestedPath)
    ? requestedPath === "/" || requestedPath === "/dashboard"
      ? "/needs-attention"
      : requestedPath
    : "/needs-attention";
}

function redirectToLogin(origin: string, errorCode: string) {
  const loginUrl = new URL("/login", origin);
  loginUrl.searchParams.set("error", errorCode);
  return NextResponse.redirect(loginUrl);
}

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const nextPath = normalizeNextPath(searchParams.get("next"));

  if (!code) {
    return redirectToLogin(origin, "missing_auth_code");
  }

  const supabase = await createSupabaseServerClient();
  const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
  if (exchangeError) {
    await clearSession();
    await logUserAccessEvent({
      eventType: "sign_in",
      status: "failed",
      routePath: "/auth/callback",
      metadata: {
        reason: "oauth_exchange_failed",
      },
    });
    return redirectToLogin(origin, "oauth_exchange_failed");
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    await clearSession();
    await logUserAccessEvent({
      eventType: "sign_in",
      status: "failed",
      routePath: "/auth/callback",
      metadata: {
        reason: "missing_user",
      },
    });
    return redirectToLogin(origin, "missing_user");
  }

  const appUser = await syncAuthorizedUser(user);
  if (!appUser) {
    await logUserAccessEvent({
      eventType: "sign_in",
      status: "denied",
      routePath: "/auth/callback",
      userEmail: user.email ?? null,
      metadata: {
        reason: "not_allowlisted",
      },
    });
    await clearSession();
    return redirectToLogin(origin, "access_denied");
  }

  await logUserAccessEvent({
    currentUser: appUser,
    eventType: "sign_in",
    status: "success",
    routePath: "/auth/callback",
    metadata: {
      destination: getPostLoginPath(appUser.role, nextPath),
    },
  });

  return NextResponse.redirect(new URL(getPostLoginPath(appUser.role, nextPath), origin));
}
