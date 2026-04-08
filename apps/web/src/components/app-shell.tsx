import Link from "next/link";

import { SidebarNav } from "@/components/sidebar-nav";
import { logoutAction } from "@/lib/auth-actions";
import type { AppUser } from "@/lib/auth";
import { getNavigationItemsForRole } from "@/lib/navigation";

export function AppShell({
  children,
  currentUser,
}: Readonly<{
  children: React.ReactNode;
  currentUser: AppUser;
}>) {
  const navigationItems = getNavigationItemsForRole(currentUser.role);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__eyebrow">Internal Tool</span>
          <Link className="sidebar__title" href="/needs-attention">
            TMC Email Monitor
          </Link>
        </div>

        <SidebarNav items={navigationItems} />

        <div className="sidebar__footer">
          <p className="sidebar__copy">
            Signed in as {currentUser.email} ({currentUser.role}).
          </p>

          <form action={logoutAction}>
            <button className="ghost-button" type="submit">
              Sign Out
            </button>
          </form>
        </div>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
