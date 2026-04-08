import { DashboardFiltersPanel } from "@/components/dashboard-filters";
import { ThreadList } from "@/components/thread-list";
import { logUserAccessEvent } from "@/lib/access-audit";
import { requireRole } from "@/lib/auth";
import {
  buildReturnToPath,
  getDashboardMetrics,
  getThreadsForDashboard,
  parseDashboardFilters,
} from "@/lib/dashboard-data";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function NotPromotedPage({
  searchParams,
}: Readonly<{
  searchParams: SearchParams;
}>) {
  const currentUser = await requireRole("admin", {
    accessPath: "/not-promoted",
  });
  await logUserAccessEvent({
    currentUser,
    eventType: "route_access",
    status: "success",
    routePath: "/not-promoted",
  });

  const resolvedSearchParams = await searchParams;
  const filters = parseDashboardFilters(resolvedSearchParams);
  const returnTo = buildReturnToPath("/not-promoted", resolvedSearchParams);

  const [threads, metrics] = await Promise.all([
    getThreadsForDashboard("not_promoted", filters, 40),
    getDashboardMetrics(),
  ]);

  return (
    <div className="content__inner">
      <header className="page-header">
        <span className="page-header__eyebrow">Not Promoted</span>
        <h1>Included threads that never entered the open queue</h1>
        <p>
          These threads remain in the corpus but were not promoted into Needs
          Attention. Admins can still move one to open when context suggests it
          should become operational.
        </p>
      </header>

      <section className="grid grid--two">
        <article className="metric-card">
          <span className="metric-card__label">Not Promoted</span>
          <strong className="metric-card__value">{metrics.notPromoted}</strong>
          <p className="metric-card__copy">
            Threads with promotion_state not_promoted and no prior open state.
          </p>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Open Queue</span>
          <strong className="metric-card__value">{metrics.needsAttention}</strong>
          <p className="metric-card__copy">
            Current Needs Attention count for comparison.
          </p>
        </article>
      </section>

      <DashboardFiltersPanel
        dashboard="not_promoted"
        filters={filters}
        key={returnTo}
      />

      <ThreadList
        dashboard="not_promoted"
        emptyMessage="No not-promoted threads match the current filters."
        items={threads}
        returnTo={returnTo}
      />
    </div>
  );
}
