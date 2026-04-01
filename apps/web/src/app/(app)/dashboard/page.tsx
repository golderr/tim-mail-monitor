export default function DashboardPage() {
  return (
    <div className="content__inner">
      <header className="page-header">
        <span className="page-header__eyebrow">Dashboard</span>
        <h1>Mailbox visibility for approved staff</h1>
        <p>
          Milestone 1 only establishes the shell. These cards represent the
          future areas where message sync, reply-state tracking, and staff
          workflows will surface.
        </p>
      </header>

      <section className="grid grid--three">
        <article className="metric-card">
          <span className="metric-card__label">Mailbox Sync</span>
          <strong className="metric-card__value">Not Connected</strong>
          <span className="status-pill status-pill--warning">
            Placeholder
          </span>
          <p className="metric-card__copy">
            Microsoft Graph polling will be introduced after the DB and auth
            layers are in place.
          </p>
        </article>

        <article className="metric-card">
          <span className="metric-card__label">Thread Workflow</span>
          <strong className="metric-card__value">0 Active Queues</strong>
          <span className="status-pill status-pill--success">
            Shell Ready
          </span>
          <p className="metric-card__copy">
            Navigation and placeholder routes are ready for stateful thread
            views and staff actions.
          </p>
        </article>

        <article className="metric-card">
          <span className="metric-card__label">Auth Model</span>
          <strong className="metric-card__value">Stubbed</strong>
          <span className="status-pill status-pill--danger">
            Replace Before Production
          </span>
          <p className="metric-card__copy">
            The current session flow is intentionally fake and exists only to
            support layout scaffolding.
          </p>
        </article>
      </section>

      <section className="grid grid--two">
        <article className="panel">
          <div className="page-header">
            <span className="page-header__eyebrow">Next Build Areas</span>
            <h1>Milestone 2 priorities</h1>
            <p>
              The worker, database, and dashboard can now evolve against an
              explicit repo structure instead of a blank project.
            </p>
          </div>
        </article>

        <article className="panel">
          <div className="list">
            <div className="list-item">
              <strong>Role-backed authentication</strong>
              <span>
                Replace the placeholder session with real staff auth and
                authorization gates.
              </span>
            </div>
            <div className="list-item">
              <strong>Core thread schema</strong>
              <span>
                Add initial Supabase migrations for profiles, roles, threads,
                messages, and status tracking.
              </span>
            </div>
            <div className="list-item">
              <strong>Worker ingestion loop</strong>
              <span>
                Connect Graph polling only after auth and persistence contracts
                are defined.
              </span>
            </div>
          </div>
        </article>
      </section>
    </div>
  );
}

