import { SectionPage } from "@/components/section-page";

export default function DigestHistoryPage() {
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

