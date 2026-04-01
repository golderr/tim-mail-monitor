import { SectionPage } from "@/components/section-page";

export default function AdminPage() {
  return (
    <SectionPage
      eyebrow="Admin"
      title="Internal settings and role controls"
      description="This page is reserved for role-based access management, mailbox configuration, sync settings, and operational tooling."
      highlights={[
        "Role-based auth is planned but not implemented yet",
        "Supabase and Microsoft credentials stay in environment configuration",
        "Future staff approval and permissions workflows will land here",
      ]}
    />
  );
}

