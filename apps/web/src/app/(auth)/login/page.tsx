import { redirect } from "next/navigation";

import { LoginWithMicrosoftButton } from "@/components/login-with-microsoft-button";
import { getCurrentUser } from "@/lib/auth";

const ERROR_MESSAGES: Record<string, string> = {
  access_denied:
    "Your Microsoft account is not on the current pilot allowlist. Contact Nick if you should have access.",
  missing_auth_code: "Microsoft sign-in did not return an auth code.",
  oauth_exchange_failed: "The Microsoft sign-in handshake failed. Please try again.",
  missing_user: "Microsoft sign-in completed, but no user profile was returned.",
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function LoginPage({
  searchParams,
}: Readonly<{
  searchParams: SearchParams;
}>) {
  if (await getCurrentUser()) {
    redirect("/needs-attention");
  }

  const resolvedSearchParams = await searchParams;
  const errorCode = normalizeParam(resolvedSearchParams.error);
  const errorMessage =
    (errorCode && ERROR_MESSAGES[errorCode]) ||
    (errorCode ? "Unable to sign you in." : null);

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-card__intro">
          <span className="page-header__eyebrow">Pilot Access</span>
          <h1>TMC Email Monitor</h1>
          <p>
            Sign in with your TCG Microsoft account. Access is limited to the
            allowlisted pilot users configured in Supabase.
          </p>
        </div>

        {errorMessage ? <p className="field-note">{errorMessage}</p> : null}

        <LoginWithMicrosoftButton />
      </section>
    </main>
  );
}
