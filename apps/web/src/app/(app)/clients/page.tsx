import { SectionPage } from "@/components/section-page";
import { logUserAccessEvent } from "@/lib/access-audit";
import { requireRole } from "@/lib/auth";

export default async function ClientsPage() {
  const currentUser = await requireRole("admin", {
    accessPath: "/clients",
  });
  await logUserAccessEvent({
    currentUser,
    eventType: "route_access",
    status: "success",
    routePath: "/clients",
  });

  return (
    <SectionPage
      eyebrow="Clients"
      title="Client directory and communication rollups"
      description="This area will map external contacts and organizations to message history, active threads, assignments, and related projects."
      highlights={[
        "Will connect mailbox threads to CRM-style context later",
        "Planned to support client-specific notes and staffing visibility",
        "Schema planning lives in the docs folder for now",
      ]}
    />
  );
}
