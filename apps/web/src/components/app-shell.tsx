import Link from "next/link";

import { SidebarNav } from "@/components/sidebar-nav";
import { logoutAction } from "@/lib/auth-actions";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__eyebrow">Internal Tool</span>
          <Link className="sidebar__title" href="/dashboard">
            Tim Mail Monitor
          </Link>
          <p className="sidebar__copy">
            Milestone 1 layout for mailbox monitoring, staff review, and
            future role-scoped workflows.
          </p>
        </div>

        <SidebarNav />

        <div className="sidebar__footer">
          <p className="sidebar__copy">
            Placeholder access only. Replace with real auth before any live
            mailbox data is connected.
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

