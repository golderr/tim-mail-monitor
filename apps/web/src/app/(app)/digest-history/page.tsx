import { SectionPage } from "@/components/section-page";
import { logUserAccessEvent } from "@/lib/access-audit";
import { requireRole } from "@/lib/auth";

export default async function DigestHistoryPage() {
  const currentUser = await requireRole("admin", {
    accessPath: "/digest-history",
  });
  await logUserAccessEvent({
    currentUser,
    eventType: "route_access",
    status: "success",
    routePath: "/digest-history",
  });

  return (
    <SectionPage
      eyebrow="Digest History"
      title="Sent summaries and daily brief records"
      description="The eventual digest system will track generated summaries, delivery metadata, and which staff received or reviewed each digest."
      highlights={[
        "Planned companion to future Teams notifications",
        "Useful for accountability and historical review",
        "No generation logic is included in Milestone 1",
      ]}
    />
  );
}
