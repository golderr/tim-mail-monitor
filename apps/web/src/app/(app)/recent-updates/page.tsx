import { SectionPage } from "@/components/section-page";

export default function RecentUpdatesPage() {
  return (
    <SectionPage
      eyebrow="Recent Updates"
      title="Recent mailbox activity summary"
      description="This page is reserved for a time-ordered view of newly ingested messages, thread changes, digest events, and internal staff updates."
      highlights={[
        "Will eventually show the latest synchronized mail events",
        "Useful for triage, daily review, and audit visibility",
        "Milestone 1 includes only navigation and layout scaffolding",
      ]}
    />
  );
}

