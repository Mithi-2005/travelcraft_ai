import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthContext } from "../state/AuthContext";

const accountBenefits = [
  "A personal dashboard that remembers how you like to travel and keeps every trip in one place.",
  "Smarter itineraries that build on your budget, interests, and preferred pace over time.",
  "A private planning space where each new trip feels more tailored than the last.",
];

function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuthContext();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await register(form);
      navigate("/dashboard", { replace: true });
    } catch (submitError) {
      setError(submitError.message || "Unable to create account.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-shell">
      <section className="mx-auto grid max-w-[980px] items-stretch gap-6 lg:grid-cols-[1fr_0.82fr]">
        <div className="soft-panel h-full p-6 sm:p-8">
          <p className="eyebrow">Create Account</p>
          <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-white sm:text-4xl">
            Start building your personal travel memory.
          </h1>
          <p className="mt-4 text-sm leading-7 text-white/60">
            Create your account once, then let TravelCraft learn your tastes so every future itinerary feels more personal and more intentional.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-white/70">Name</label>
              <input
                className="input-shell"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Avery Parker"
              />
            </div>

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
                placeholder="At least 8 characters"
              />
            </div>

            {error ? (
              <div className="rounded-lg border border-coral/30 bg-coral/10 p-4 text-sm text-coral">{error}</div>
            ) : null}

            <button className="button-primary w-full" type="submit" disabled={submitting}>
              {submitting ? "Creating account..." : "Create Account"}
            </button>
          </form>
        </div>

        <div className="lux-panel h-full p-6 sm:p-8">
          <p className="eyebrow">What You Unlock</p>
          <div className="mt-6 space-y-4">
            {accountBenefits.map((item) => (
              <div key={item} className="rounded-lg border border-white/10 bg-black/20 p-4 text-sm leading-7 text-white/62">
                {item}
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm text-white/56">
            Already registered?{" "}
            <Link className="font-semibold text-glow" to="/login">
              Sign in here
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  );
}

export default RegisterPage;
