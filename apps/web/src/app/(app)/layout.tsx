import { AppShell } from "@/components/app-shell";
import { requireSession } from "@/lib/auth";

export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  await requireSession();

  return <AppShell>{children}</AppShell>;
}

