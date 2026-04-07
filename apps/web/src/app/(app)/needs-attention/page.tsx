import { DashboardFiltersPanel } from "@/components/dashboard-filters";
import { ThreadList } from "@/components/thread-list";
import {
  buildReturnToPath,
  getDashboardMetrics,
  getThreadsForDashboard,
  parseDashboardFilters,
} from "@/lib/dashboard-data";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function NeedsAttentionPage({
  searchParams,
}: Readonly<{
  searchParams: SearchParams;
}>) {
  const resolvedSearchParams = await searchParams;
  const filters = parseDashboardFilters(resolvedSearchParams);
  const returnTo = buildReturnToPath("/needs-attention", resolvedSearchParams);

  const [threads, metrics] = await Promise.all([
    getThreadsForDashboard("needs_attention", filters, 40),
    getDashboardMetrics(),
  ]);

  return (
    <div className="content__inner">
      <header className="page-header">
        <span className="page-header__eyebrow">Needs Attention</span>
        <h1>Open threads that require staff attention.</h1>
        <p>
          If a thread is open, it lives here. If it is handled or disregarded,
          it moves out.
        </p>
      </header>

      <section className="grid grid--two">
        <article className="metric-card">
          <span className="metric-card__label">Open Threads</span>
          <strong className="metric-card__value">{metrics.needsAttention}</strong>
          <p className="metric-card__copy">
            Threads whose current review state is open.
          </p>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Urgent Open</span>
          <strong className="metric-card__value">{metrics.urgentOpen}</strong>
          <p className="metric-card__copy">
            Open threads carrying at least one urgent event tag.
          </p>
        </article>
      </section>

      <DashboardFiltersPanel
        dashboard="needs_attention"
        filters={filters}
        openPrimaryEventTagCounts={metrics.openPrimaryEventTagCounts}
        openNoConsultingStaffCount={metrics.openNoConsultingStaffCount}
        key={returnTo}
      />

      <ThreadList
        dashboard="needs_attention"
        emptyMessage="No open threads match the current filters."
        items={threads}
        returnTo={returnTo}
      />
    </div>
  );
}
