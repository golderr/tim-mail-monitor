type SectionPageProps = {
  eyebrow: string;
  title: string;
  description: string;
  highlights: string[];
};

export function SectionPage({
  eyebrow,
  title,
  description,
  highlights,
}: SectionPageProps) {
  return (
    <div className="content__inner">
      <header className="page-header">
        <span className="page-header__eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>

      <section className="grid grid--three">
        {highlights.map((highlight, index) => (
          <article className="placeholder-card" key={highlight}>
            <span className="placeholder-card__label">Placeholder {index + 1}</span>
            <p className="placeholder-card__copy">{highlight}</p>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="list">
          <div className="list-item">
            <strong>Why this exists now</strong>
            <span>
              Milestone 1 sets route structure, page ownership, and navigation
              without committing to incomplete backend behavior.
            </span>
          </div>
          <div className="list-item">
            <strong>What comes next</strong>
            <span>
              This page will receive real data once auth, schema, and worker
              contracts are implemented in the next milestone.
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}

