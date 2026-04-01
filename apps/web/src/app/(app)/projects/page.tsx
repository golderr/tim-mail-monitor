import { SectionPage } from "@/components/section-page";

export default function ProjectsPage() {
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

