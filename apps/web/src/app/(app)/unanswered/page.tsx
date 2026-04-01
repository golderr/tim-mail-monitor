import { SectionPage } from "@/components/section-page";

export default function UnansweredPage() {
  return (
    <SectionPage
      eyebrow="Unanswered"
      title="Open external messages without a recorded reply"
      description="Future reply-state logic will classify threads that have not been answered within expected windows and route them to staff."
      highlights={[
        "Depends on normalized message authorship and thread reconstruction",
        "Will likely include aging buckets and owner filters",
        "Kept intentionally empty until the worker and schema are real",
      ]}
    />
  );
}

