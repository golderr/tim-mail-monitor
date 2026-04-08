function requireValue(name: string, value: string | undefined) {
  if (!value) {
    throw new Error(`Missing required Supabase config: ${name}`);
  }

  return value;
}

export function getSupabaseConfig() {
  return {
    url: requireValue(
      "NEXT_PUBLIC_SUPABASE_URL",
      process.env.NEXT_PUBLIC_SUPABASE_URL,
    ),
    publishableKey: requireValue(
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
    ),
  };
}
