import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const SESSION_COOKIE_NAME = "tim_mail_monitor_session";
const SESSION_COOKIE_VALUE = "approved";

export async function hasSession() {
  const cookieStore = await cookies();

  return cookieStore.get(SESSION_COOKIE_NAME)?.value === SESSION_COOKIE_VALUE;
}

export async function requireSession() {
  if (!(await hasSession())) {
    redirect("/login");
  }
}

export async function createDemoSession() {
  const cookieStore = await cookies();

  cookieStore.set(SESSION_COOKIE_NAME, SESSION_COOKIE_VALUE, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
}

export async function clearDemoSession() {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE_NAME);
}

