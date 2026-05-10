import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import CarouselArrowButton from "../components/ui/CarouselArrowButton";
import { PanelSkeleton } from "../components/ui/LoadingSkeleton";
import { formatCurrency } from "../lib/currency";
import { useAppContext } from "../state/AppContext";

const slideTransition = {
  type: "spring",
  stiffness: 280,
  damping: 28,
};

const slideVariants = {
  enter: (direction) => ({
    opacity: 0,
    x: direction > 0 ? 56 : -56,
  }),
  center: {
    opacity: 1,
    x: 0,
  },
  exit: (direction) => ({
    opacity: 0,
    x: direction > 0 ? -56 : 56,
  }),
};

function MemoryPage() {
  const { memory, loadingMemory, saveMemory } = useAppContext();
  const [form, setForm] = useState({
    name: "",
    bio: "",
    home_airport: "",
    budget_preference: "",
    travel_style: "",
    interests: "",
    preferred_mood: "relaxed",
  });
  const [status, setStatus] = useState("");
  const [tripIndex, setTripIndex] = useState(0);
  const [tripDirection, setTripDirection] = useState(1);
  const trips = memory?.past_trips || [];
  const activeTrip = trips[tripIndex] || null;

  useEffect(() => {
    if (!memory) return;
    setForm({
      name: memory.name || "",
      bio: memory.bio || "",
      home_airport: memory.home_airport || "",
      budget_preference: memory.budget_preference ?? "",
      travel_style: memory.travel_style || "",
      interests: (memory.interests || []).join(", "),
      preferred_mood: memory.preferred_mood || "relaxed",
    });
  }, [memory]);

  useEffect(() => {
    if (!trips.length) {
      setTripIndex(0);
      return;
    }

    if (tripIndex > trips.length - 1) {
      setTripIndex(trips.length - 1);
    }
  }, [tripIndex, trips]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("Saving...");
    try {
      await saveMemory({
        ...form,
        budget_preference: form.budget_preference === "" ? null : Number(form.budget_preference),
        interests: form.interests
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setStatus("Memory updated.");
    } catch (error) {
      setStatus(error.message || "Unable to save memory.");
    }
    setTimeout(() => setStatus(""), 1800);
  };

  const showPreviousTrip = () => {
    setTripDirection(-1);
    setTripIndex((current) => (current === 0 ? trips.length - 1 : current - 1));
  };

  const showNextTrip = () => {
    setTripDirection(1);
    setTripIndex((current) => (current + 1) % trips.length);
  };

  const jumpToTrip = (index) => {
    if (index === tripIndex) return;
    setTripDirection(index > tripIndex ? 1 : -1);
    setTripIndex(index);
  };

  if (loadingMemory) {
    return (
      <div className="page-shell grid gap-6 lg:grid-cols-2">
        <PanelSkeleton />
        <PanelSkeleton />
      </div>
    );
  }

  return (
    <div className="page-shell">
      <section className="page-stack">
        <form onSubmit={handleSubmit} className="lux-panel p-6 sm:p-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="eyebrow">Memento Memory</p>
              <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
                Edit the profile behind every itinerary.
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/60">
                These preferences shape future suggestions, pacing, and trip mood defaults.
              </p>
            </div>
            {status ? <p className="section-card text-sm text-white/66">{status}</p> : null}
          </div>

          <div className="form-layout mt-8">
            <div>
              <label className="field-label">Name</label>
              <input
                className="input-shell"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              />
            </div>
            <div>
              <label className="field-label">Home Airport</label>
              <input
                className="input-shell"
                value={form.home_airport}
                onChange={(event) => setForm((current) => ({ ...current, home_airport: event.target.value }))}
              />
            </div>
            <div className="field-full">
              <label className="field-label">Bio</label>
              <textarea
                className="input-shell min-h-[120px]"
                value={form.bio}
                onChange={(event) => setForm((current) => ({ ...current, bio: event.target.value }))}
              />
            </div>
            <div>
              <label className="field-label">Budget Preference (INR)</label>
              <input
                className="input-shell"
                type="number"
                value={form.budget_preference}
                onChange={(event) => setForm((current) => ({ ...current, budget_preference: event.target.value }))}
                placeholder="22000"
              />
            </div>
            <div>
              <label className="field-label">Preferred Mood</label>
              <select
                className="input-shell"
                value={form.preferred_mood}
                onChange={(event) => setForm((current) => ({ ...current, preferred_mood: event.target.value }))}
              >
                <option value="relaxed">Relaxed</option>
                <option value="adventure">Adventure</option>
                <option value="luxury">Luxury</option>
              </select>
            </div>
            <div className="field-full">
              <label className="field-label">Interests</label>
              <input
                className="input-shell"
                value={form.interests}
                onChange={(event) => setForm((current) => ({ ...current, interests: event.target.value }))}
                placeholder="food, architecture, wellness"
              />
            </div>
            <div className="field-full">
              <label className="field-label">Travel Style</label>
              <textarea
                className="input-shell min-h-[110px]"
                value={form.travel_style}
                onChange={(event) => setForm((current) => ({ ...current, travel_style: event.target.value }))}
              />
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button data-cursor="active" className="button-primary w-full sm:w-auto" type="submit">
              Save Memory Profile
            </button>
          </div>
        </form>

        <div className="grid items-stretch gap-6 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="soft-panel flex min-h-[360px] max-h-[490px] flex-col p-8">
            <p className="eyebrow">Stored Insights</p>
            <div className="mt-5 flex-1 space-y-4 overflow-y-auto pr-1">
              {(memory?.insights || []).map((insight) => (
                <div key={insight} className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-7 text-white/65">
                  {insight}
                </div>
              ))}
            </div>
          </div>

          <div className="lux-panel flex min-h-[360px] max-h-[490px] flex-col overflow-hidden p-8">
            <p className="eyebrow">Trip Library</p>
            <div className="mt-5 flex flex-1 flex-col">
              {activeTrip ? (
                <>
                  <div className="carousel-shell flex flex-1 flex-col justify-center px-0 sm:px-6">
                    <CarouselArrowButton
                      direction="left"
                      label="Show previous saved trip"
                      className="carousel-arrow-left"
                      onClick={showPreviousTrip}
                    />
                    <CarouselArrowButton
                      direction="right"
                      label="Show next saved trip"
                      className="carousel-arrow-right"
                      onClick={showNextTrip}
                    />
                    <AnimatePresence initial={false} custom={tripDirection} mode="wait">
                      <motion.div
                        key={activeTrip.trip_id}
                        custom={tripDirection}
                        variants={slideVariants}
                        initial="enter"
                        animate="center"
                        exit="exit"
                        transition={slideTransition}
                        className="flex flex-1"
                      >
                        <Link
                          to={`/trip/${activeTrip.trip_id}`}
                          className="block flex-1 rounded-lg border border-white/10 bg-black/25 p-5 transition hover:border-glow/35 hover:bg-white/[0.06]"
                        >
                          <div className="flex h-full flex-col justify-between gap-8">
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <p className="font-display text-2xl font-bold tracking-[-0.05em]">{activeTrip.destination}</p>
                                <p className="mt-1 text-sm text-white/45 capitalize">
                                  {activeTrip.mood} | {activeTrip.days} days | {activeTrip.traveler_count === 1 ? "1 traveler" : `${activeTrip.traveler_count} travelers`} | {formatCurrency(activeTrip.budget, activeTrip.currency_code)}
                                </p>
                              </div>
                              <div className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/45">
                                {trips.length} trips
                              </div>
                            </div>
                            <div className="grid gap-3 sm:grid-cols-2">
                              <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3">
                                <p className="text-xs uppercase tracking-[0.22em] text-white/40">Best Time</p>
                                <p className="mt-2 text-sm leading-6 text-white/68">{activeTrip.best_time_to_visit}</p>
                              </div>
                              <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3">
                                <p className="text-xs uppercase tracking-[0.22em] text-white/40">Top Interests</p>
                                <p className="mt-1 text-sm text-white/45 capitalize">
                                  {(activeTrip.interests || []).slice(0, 3).join(", ") || "General discovery"}
                                </p>
                              </div>
                            </div>
                            <div className="flex justify-end">
                              <span className="button-secondary h-fit">View Detail</span>
                            </div>
                          </div>
                        </Link>
                      </motion.div>
                    </AnimatePresence>
                  </div>
                  <div className="mt-4 flex gap-2">
                    {trips.map((trip, index) => (
                      <button
                        key={trip.trip_id}
                        type="button"
                        aria-label={`Go to saved trip ${index + 1}`}
                        onClick={() => jumpToTrip(index)}
                        className={`h-2 flex-1 rounded-full transition ${
                          index === tripIndex ? "bg-glow" : "bg-white/15 hover:bg-white/25"
                        }`}
                      />
                    ))}
                  </div>
                </>
              ) : (
                <div className="w-full rounded-lg border border-dashed border-white/12 p-6 text-sm text-white/55">
                  No saved trips yet. Generate your first itinerary and it will appear here with a dedicated detailed view.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default MemoryPage;
