import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthContext } from "../state/AuthContext";

const sessionBenefits = [
  "Return to your saved preferences, trip mood, and favorite planning patterns in seconds.",
  "Open past itineraries, revisit highlights, and continue refining future trips without starting over.",
  "Keep your planning flow personal, calm, and consistent across every session.",
];

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuthContext();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const redirectTarget = location.state?.from?.pathname || "/dashboard";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await login(form);
      navigate(redirectTarget, { replace: true });
    } catch (submitError) {
      setError(submitError.message || "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <section className="mx-auto grid max-w-[980px] items-stretch gap-6 lg:grid-cols-[1fr_0.82fr]">
        <div className="lux-panel h-full p-6 sm:p-8">
          <p className="eyebrow">Sign In</p>
          <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-white sm:text-4xl">
            Welcome back to TravelCraft AI.
          </h1>
          <p className="mt-4 text-sm leading-7 text-white/60">
            Pick up right where you left off, with your saved travel preferences, trip history, and planning style ready to guide the next journey.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-white/70">Email</label>
              <input
                className="input-shell"
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-white/70">Password</label>
              <input
                className="input-shell"
                type="password"
                value={form.password}
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="Minimum 8 characters"
              />
            </div>

            {error ? (
              <div className="rounded-lg border border-coral/30 bg-coral/10 p-4 text-sm text-coral">{error}</div>
            ) : null}

            <button className="button-primary w-full" type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>

        <div className="soft-panel h-full p-6 sm:p-8">
          <p className="eyebrow">Why Sign In</p>
          <h2 className="mt-3 font-display text-2xl font-bold tracking-[-0.04em] text-white">Your planning memory, ready when you are</h2>
          <div className="mt-6 space-y-4">
            {sessionBenefits.map((item) => (
              <div key={item} className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-7 text-white/62">
                {item}
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm text-white/56">
            Need an account?{" "}
            <Link className="font-semibold text-glow" to="/register">
              Create one here
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  );
}

export default LoginPage;
