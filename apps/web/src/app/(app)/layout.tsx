import { AppShell } from "@/components/app-shell";
import { requireAnyRole } from "@/lib/auth";

export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const currentUser = await requireAnyRole(["admin", "lead"]);

  return <AppShell currentUser={currentUser}>{children}</AppShell>;
}
