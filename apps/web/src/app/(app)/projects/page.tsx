import { SectionPage } from "@/components/section-page";
import { logUserAccessEvent } from "@/lib/access-audit";
import { requireRole } from "@/lib/auth";

export default async function ProjectsPage() {
  const currentUser = await requireRole("admin", {
    accessPath: "/projects",
  });
  await logUserAccessEvent({
    currentUser,
    eventType: "route_access",
    status: "success",
    routePath: "/projects",
  });

  return (
    <SectionPage
      eyebrow="Projects"
      title="Project-linked communication views"
      description="Projects will eventually group related mail threads, clients, statuses, and internal notes so staff can see communication in context."
      highlights={[
        "Expected to share data contracts with clients and thread tables",
        "Will support scoped dashboards for active deal work",
        "Milestone 1 keeps this as a routed placeholder only",
      ]}
    />
  );
}
