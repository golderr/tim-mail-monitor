export const EVENT_TAG_OPTIONS = [
  { value: "deadline", label: "Deadline" },
  { value: "draft_needed", label: "Draft Needed" },
  { value: "meeting_request", label: "Meeting Request" },
  { value: "scope_change", label: "Scope Change" },
  { value: "client_materials", label: "Client Materials" },
  { value: "status_request", label: "Status Request" },
  { value: "commitment", label: "Commitment" },
  { value: "cancellation_pause", label: "Cancellation/Pause" },
  { value: "proposal_request", label: "Proposal Request" },
  { value: "new_project", label: "New Project" },
] as const;

export const EVENT_LABELS: Record<string, string> = Object.fromEntries(
  EVENT_TAG_OPTIONS.map((option) => [option.value, option.label]),
);

export const NO_CONSULTING_STAFF_LABEL = "No Consulting Staff";
