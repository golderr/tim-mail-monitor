import { SectionPage } from "@/components/section-page";

export default function ClientsPage() {
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

