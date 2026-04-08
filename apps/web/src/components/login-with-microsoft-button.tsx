"use client";

import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

export function LoginWithMicrosoftButton() {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSignIn() {
    setPending(true);
    setError(null);

    const supabase = createClient();
    const redirectTo = `${window.location.origin}/auth/callback?next=/needs-attention`;
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: "azure",
      options: {
        scopes: "email",
        redirectTo,
      },
    });

    if (signInError) {
      setError(signInError.message);
      setPending(false);
    }
  }

  return (
    <div className="grid">
      <button
        className="primary-button"
        disabled={pending}
        onClick={handleSignIn}
        type="button"
      >
        {pending ? "Redirecting..." : "Continue With Microsoft"}
      </button>
      {error ? <p className="field-note">{error}</p> : null}
    </div>
  );
}
