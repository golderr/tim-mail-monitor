import { DashboardFiltersPanel } from "@/components/dashboard-filters";
import { ThreadList } from "@/components/thread-list";
import {
  buildReturnToPath,
  getDashboardMetrics,
  getThreadsForDashboard,
  parseDashboardFilters,
} from "@/lib/dashboard-data";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function ClosedPage({
  searchParams,
}: Readonly<{
  searchParams: SearchParams;
}>) {
  const resolvedSearchParams = await searchParams;
  const filters = parseDashboardFilters(resolvedSearchParams);
  const returnTo = buildReturnToPath("/closed", resolvedSearchParams);

  const [threads, metrics] = await Promise.all([
    getThreadsForDashboard("closed", filters, 40),
    getDashboardMetrics(),
  ]);

  return (
    <div className="content__inner">
      <header className="page-header">
        <span className="page-header__eyebrow">Closed</span>
        <h1>Previously active threads that were handled, disregarded, or expired</h1>
        <p>
          Closed is strictly for threads that were opened at some point and then
          moved out of the active queue.
        </p>
      </header>

      <section className="grid grid--two">
        <article className="metric-card">
          <span className="metric-card__label">Closed Threads</span>
          <strong className="metric-card__value">{metrics.closed}</strong>
          <p className="metric-card__copy">
            Threads with review_state handled, disregard, or expired after ever being open.
          </p>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Last Sync</span>
          <strong className="metric-card__value">{metrics.lastSyncStatus}</strong>
          <p className="metric-card__copy">
            {metrics.lastSyncAt
              ? `Completed ${new Date(metrics.lastSyncAt).toLocaleString()}`
              : "No completed sync is recorded yet."}
          </p>
        </article>
      </section>

      <DashboardFiltersPanel dashboard="closed" filters={filters} key={returnTo} />

      <ThreadList
        dashboard="closed"
        emptyMessage="No closed threads match the current filters."
        items={threads}
        returnTo={returnTo}
      />
    </div>
  );
}
