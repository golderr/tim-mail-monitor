export const navigationItems = [
  {
    href: "/dashboard",
    label: "Dashboard",
    description: "High-level mailbox and workflow overview.",
  },
  {
    href: "/needs-attention",
    label: "Needs Attention",
    description: "Priority threads requiring staff review.",
  },
  {
    href: "/recent-updates",
    label: "Recent Updates",
    description: "Latest activity across synced communications.",
  },
  {
    href: "/unanswered",
    label: "Unanswered",
    description: "Threads without a recorded external reply.",
  },
  {
    href: "/clients",
    label: "Clients",
    description: "Client-level communication and context views.",
  },
  {
    href: "/projects",
    label: "Projects",
    description: "Project-linked mail and ownership surfaces.",
  },
  {
    href: "/digest-history",
    label: "Digest History",
    description: "Sent summaries and reporting placeholders.",
  },
  {
    href: "/admin",
    label: "Admin",
    description: "Future configuration and role management area.",
  },
] as const;
