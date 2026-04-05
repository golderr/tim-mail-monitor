"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { DashboardFilters, DashboardName } from "@/lib/dashboard-data";

const TAG_OPTIONS = [
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

const DATE_WINDOWS = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 14 days", days: 14 },
  { label: "Last 30 days", days: 30 },
] as const;

function formatDateInput(date: Date) {
  return date.toISOString().slice(0, 10);
}

export function DashboardFiltersPanel({
  dashboard,
  filters,
}: Readonly<{
  dashboard: DashboardName;
  filters: DashboardFilters;
}>) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [client, setClient] = useState(filters.client ?? "");
  const [projectNumber, setProjectNumber] = useState(filters.projectNumber ?? "");

  const selectedTags = useMemo(() => filters.tags ?? [], [filters.tags]);

  const updateQuery = useCallback(
    (next: Record<string, string | string[] | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());

      for (const [key, value] of Object.entries(next)) {
        params.delete(key);
        if (!value) {
          continue;
        }

        const entries = Array.isArray(value) ? value : [value];
        for (const entry of entries) {
          if (entry) {
            params.append(key, entry);
          }
        }
      }

      const queryString = params.toString();
      router.replace(queryString ? `${pathname}?${queryString}` : pathname);
    },
    [pathname, router, searchParams],
  );

  useEffect(() => {
    const handle = window.setTimeout(() => {
      updateQuery({
        client: client || undefined,
        projectNumber: projectNumber || undefined,
      });
    }, 350);

    return () => window.clearTimeout(handle);
  }, [client, projectNumber, updateQuery]);

  return (
    <section className="panel filters-panel">
      <div className="filters-inline">
        <label className="filters-inline__field">
          <span>Client</span>
          <input
            onChange={(event) => setClient(event.target.value)}
            placeholder="Client"
            value={client}
          />
        </label>

        <label className="filters-inline__field">
          <span>Project</span>
          <input
            onChange={(event) => setProjectNumber(event.target.value)}
            placeholder="Project / p#"
            value={projectNumber}
          />
        </label>

        <label className="filters-inline__field">
          <span>Reply</span>
          <select
            onChange={(event) =>
              updateQuery({ replyState: event.target.value || undefined })
            }
            value={filters.replyState ?? ""}
          >
            <option value="">All</option>
            <option value="unanswered">Unanswered</option>
            <option value="answered">Answered</option>
            <option value="partial_answer">Partial Answer</option>
            <option value="answered_offline">Answered Offline</option>
          </select>
        </label>

        <label className="filters-inline__field">
          <span>Sort</span>
          <select
            onChange={(event) =>
              updateQuery({ sort: event.target.value || undefined })
            }
            value={filters.sort ?? "priority"}
          >
            <option value="priority">Priority</option>
            <option value="latest_desc">Latest</option>
            <option value="latest_asc">Oldest</option>
          </select>
        </label>

        {dashboard === "admin" ? (
          <>
            <label className="filters-inline__field">
              <span>Promotion</span>
              <select
                onChange={(event) =>
                  updateQuery({ promotionState: event.target.value || undefined })
                }
                value={filters.promotionState ?? ""}
              >
                <option value="">All</option>
                <option value="promoted">Promoted</option>
                <option value="not_promoted">Not Promoted</option>
              </select>
            </label>

            <label className="filters-inline__field">
              <span>Review</span>
              <select
                onChange={(event) =>
                  updateQuery({ reviewState: event.target.value || undefined })
                }
                value={filters.reviewState ?? ""}
              >
                <option value="">All</option>
                <option value="open">Open</option>
                <option value="handled">Handled</option>
                <option value="disregard">Disregard</option>
              </select>
            </label>
          </>
        ) : null}
      </div>

      <div className="filters-row">
        <span className="filters-row__label">Tags</span>
        <div className="filters-row__pills">
          {TAG_OPTIONS.map((option) => {
            const isActive = selectedTags.includes(option.value);
            return (
              <button
                className={`status-pill ${
                  isActive ? "status-pill--warning" : "status-pill--neutral"
                }`}
                key={option.value}
                onClick={() => {
                  const nextTags = isActive
                    ? selectedTags.filter((tag) => tag !== option.value)
                    : [...selectedTags, option.value];
                  updateQuery({ tag: nextTags.length > 0 ? nextTags : undefined });
                }}
                type="button"
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="filters-row">
        <span className="filters-row__label">Date</span>
        <div className="filters-row__links">
          {DATE_WINDOWS.map((windowOption) => (
            <button
              className="text-link-button"
              key={windowOption.days}
              onClick={() => {
                const fromDate = new Date();
                fromDate.setDate(fromDate.getDate() - windowOption.days);
                updateQuery({
                  dateFrom: formatDateInput(fromDate),
                  dateTo: undefined,
                });
              }}
              type="button"
            >
              {windowOption.label}
            </button>
          ))}
          <button
            className="text-link-button"
            onClick={() => updateQuery({ dateFrom: undefined, dateTo: undefined })}
            type="button"
          >
            Clear dates
          </button>
        </div>
      </div>
    </section>
  );
}
