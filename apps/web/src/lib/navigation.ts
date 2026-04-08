import type { AppRole } from "@/lib/auth";

export const navigationItems = [
  {
    href: "/needs-attention",
    label: "Needs Attention",
    description: "Open operational threads that currently need staff review.",
    roles: ["admin", "lead"],
  },
  {
    href: "/closed",
    label: "Closed",
    description: "Threads that were previously active and are now handled or disregarded.",
    roles: ["admin", "lead"],
  },
  {
    href: "/not-promoted",
    label: "Not Promoted",
    description: "Included threads that never entered the open queue.",
    roles: ["admin"],
  },
  {
    href: "/admin",
    label: "Admin",
    description: "State inspection, sync health, and override controls.",
    roles: ["admin"],
  },
] satisfies readonly {
  href: string;
  label: string;
  description: string;
  roles: readonly AppRole[];
}[];

export type NavigationItem = (typeof navigationItems)[number];

export function getNavigationItemsForRole(role: AppRole) {
  return navigationItems.filter((item) =>
    item.roles.some((itemRole) => itemRole === role),
  );
}
