"use server";

import { redirect } from "next/navigation";

import { clearDemoSession, createDemoSession } from "@/lib/auth";

export async function loginAction() {
  await createDemoSession();
  redirect("/dashboard");
}

export async function logoutAction() {
  await clearDemoSession();
  redirect("/login");
}

