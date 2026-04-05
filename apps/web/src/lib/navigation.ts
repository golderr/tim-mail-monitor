export const navigationItems = [
  {
    href: "/needs-attention",
    label: "Needs Attention",
    description: "Open operational threads that currently need staff review.",
  },
  {
    href: "/closed",
    label: "Closed",
    description: "Threads that were previously active and are now handled or disregarded.",
  },
  {
    href: "/not-promoted",
    label: "Not Promoted",
    description: "Included threads that never entered the open queue.",
  },
  {
    href: "/admin",
    label: "Admin",
    description: "State inspection, sync health, and lead-only controls.",
  },
] as const;
