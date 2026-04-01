import { SectionPage } from "@/components/section-page";

export default function NeedsAttentionPage() {
  return (
    <SectionPage
      eyebrow="Needs Attention"
      title="Critical client conversations will surface here"
      description="This queue will eventually prioritize important external threads, stalled responses, escalation signals, and principal-visible items that need staff intervention."
      highlights={[
        "Placeholder table and workflow surface only",
        "Intended future inputs: urgency filters, reply-state logic, and event detection",
        "Will support assignment, note-taking, and status updates",
      ]}
    />
  );
}

