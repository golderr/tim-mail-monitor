import { DashboardFiltersPanel } from "@/components/dashboard-filters";
import { ThreadList } from "@/components/thread-list";
import {
  buildReturnToPath,
  getDashboardMetrics,
  getThreadsForDashboard,
  parseDashboardFilters,
} from "@/lib/dashboard-data";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function AdminPage({
  searchParams,
}: Readonly<{
  searchParams: SearchParams;
}>) {
  const resolvedSearchParams = await searchParams;
  const filters = parseDashboardFilters(resolvedSearchParams);
  const returnTo = buildReturnToPath("/admin", resolvedSearchParams);

  const [threads, metrics] = await Promise.all([
    getThreadsForDashboard("admin", filters, 60),
    getDashboardMetrics(),
  ]);

  return (
    <div className="content__inner">
      <header className="page-header">
        <span className="page-header__eyebrow">Admin</span>
        <h1>Operational controls and state inspection</h1>
        <p>
          This view exposes all threads with override-aware filters so leads can
          inspect how the system classified each item and move it between review
          states when needed.
        </p>
      </header>

      <section className="grid grid--three">
        <article className="metric-card">
          <span className="metric-card__label">Needs Attention</span>
          <strong className="metric-card__value">{metrics.needsAttention}</strong>
          <p className="metric-card__copy">Current open queue count.</p>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Closed</span>
          <strong className="metric-card__value">{metrics.closed}</strong>
          <p className="metric-card__copy">
            Previously active threads now handled, disregarded, or expired.
          </p>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Latest Sync</span>
          <strong className="metric-card__value">{metrics.lastSyncStatus}</strong>
          <p className="metric-card__copy">
            {metrics.lastSyncAt
              ? `${metrics.lastSyncMessagesSeen} messages seen on ${new Date(
                  metrics.lastSyncAt,
                ).toLocaleString()}`
              : "No completed sync is recorded yet."}
          </p>
        </article>
      </section>

      <DashboardFiltersPanel dashboard="admin" filters={filters} key={returnTo} />

      <ThreadList
        dashboard="admin"
        emptyMessage="No admin rows match the current filters."
        items={threads}
        returnTo={returnTo}
      />
    </div>
  );
}
