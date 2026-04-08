"use server";

import { redirect } from "next/navigation";

import { logUserAccessEvent } from "@/lib/access-audit";
import { clearSession, getCurrentUser } from "@/lib/auth";

export async function logoutAction() {
  const currentUser = await getCurrentUser();
  if (currentUser) {
    await logUserAccessEvent({
      currentUser,
      eventType: "sign_out",
      status: "success",
      routePath: "/logout",
    });
  }
  await clearSession();
  redirect("/login");
}
