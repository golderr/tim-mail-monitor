import { loginAction } from "@/lib/auth-actions";

export default function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-card__intro">
          <span className="page-header__eyebrow">Milestone 1 Access</span>
          <h1>Tim Mail Monitor</h1>
          <p>
            This is a placeholder internal login for the Milestone 1 shell.
            Replace this with real staff authentication and role checks in the
            next milestone.
          </p>
        </div>

        <form action={loginAction} className="grid">
          <div className="field">
            <label htmlFor="email">Work Email</label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="team.member@yourfirm.com"
              required
            />
          </div>

          <p className="field-note">
            Any submitted email creates a local placeholder session right now.
          </p>

          <button className="primary-button" type="submit">
            Enter Internal Dashboard
          </button>
        </form>
      </section>
    </main>
  );
}

