import { AnimatePresence, motion } from "framer-motion";
import { useDeferredValue, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import CarouselArrowButton from "../components/ui/CarouselArrowButton";
import { PanelSkeleton } from "../components/ui/LoadingSkeleton";
import { APP_CURRENCY_CODE, formatCurrency } from "../lib/currency";
import SectionHeading from "../components/ui/SectionHeading";
import { useAppContext } from "../state/AppContext";

function buildTasteSummary(memory) {
  const interests = memory?.interests || [];
  const style = memory?.travel_style || "your evolving travel style";
  const mood = memory?.preferred_mood || "relaxed";
  const budget = memory?.budget_preference != null
    ? `around ${formatCurrency(memory.budget_preference, APP_CURRENCY_CODE)}`
    : "without a saved budget yet";

  if (interests.length) {
    return `Your memory is currently shaped by ${style}, a ${mood} trip mood, and recurring interest in ${interests.slice(0, 3).join(", ")}. TravelCraft is ready to plan with a budget ${budget}.`;
  }

  return `Your memory is currently shaped by ${style} and a ${mood} trip mood. Add a few interests in Memory to help TravelCraft sharpen the next itinerary and plan with a budget ${budget}.`;
}

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

function DashboardPage() {
  const { memory, loadingMemory, memoryError } = useAppContext();
  const deferredTrips = useDeferredValue(memory?.past_trips || []);
  const [timelineIndex, setTimelineIndex] = useState(0);
  const [timelineDirection, setTimelineDirection] = useState(1);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const activeTrip = deferredTrips[timelineIndex] || null;

  useEffect(() => {
    if (!deferredTrips.length) {
      setTimelineIndex(0);
      return;
    }

    if (timelineIndex > deferredTrips.length - 1) {
      setTimelineIndex(deferredTrips.length - 1);
    }
  }, [deferredTrips, timelineIndex]);

  const showPreviousTrip = () => {
    setTimelineDirection(-1);
    setTimelineIndex((current) => (current === 0 ? deferredTrips.length - 1 : current - 1));
  };

  const showNextTrip = () => {
    setTimelineDirection(1);
    setTimelineIndex((current) => (current + 1) % deferredTrips.length);
  };

  const jumpToTrip = (index) => {
    if (index === timelineIndex) return;
    setTimelineDirection(index > timelineIndex ? 1 : -1);
    setTimelineIndex(index);
  };

  if (loadingMemory) {
    return (
      <div className="page-shell space-y-6">
        <PanelSkeleton className="h-48" />
        <div className="grid gap-6 lg:grid-cols-3">
          <PanelSkeleton />
          <PanelSkeleton />
          <PanelSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <section className="mx-auto grid max-w-[1040px] items-stretch gap-6 lg:grid-cols-[1.12fr_0.88fr]">
        <div className="lux-panel flex h-full min-h-[360px] flex-col p-6 sm:p-8">
          <div>
            <p className="eyebrow">Dashboard</p>
            <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] text-white sm:text-4xl">
              {greeting}, {memory?.name || "traveler"}.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/62">
              {buildTasteSummary(memory)}
            </p>
          </div>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Budget Pref</p>
              <p className="mt-2 font-display text-3xl font-bold">
                {memory?.budget_preference != null ? formatCurrency(memory.budget_preference, APP_CURRENCY_CODE) : "Not set"}
              </p>
            </div>
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Trip Mood</p>
              <p className="mt-2 font-display text-3xl font-bold capitalize">{memory?.preferred_mood}</p>
            </div>
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Past Trips</p>
              <p className="mt-2 font-display text-3xl font-bold">{memory?.past_trips?.length || 0}</p>
            </div>
          </div>
        </div>

        <div className="soft-panel flex h-full min-h-[360px] flex-col p-6 sm:p-8">
          <div>
            <p className="eyebrow">Generate</p>
            <h2 className="mt-4 font-display text-3xl font-bold tracking-[-0.05em]">Create a new personalized plan</h2>
            <p className="mt-4 text-sm leading-7 text-white/60">
              Start from a destination, mood, and budget, then let the backend combine live research with
              your stored preferences.
            </p>
          </div>
          <div className="mt-8 space-y-6">
            <Link className="button-primary w-full" to="/generator">
              Generate New Plan
            </Link>
            <div className="rounded-lg border border-white/10 bg-black/25 p-5">
              <p className="text-sm text-white/68">
                {memory?.travel_style || "Save your travel style in Memory to sharpen future itineraries."}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto mt-12 grid max-w-[1040px] items-stretch gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="soft-panel flex h-full min-h-[520px] flex-col p-6 sm:p-8">
          <SectionHeading eyebrow="Preference Summary" title="The signals TravelCraft remembers." />
          <div className="mt-6 flex flex-wrap gap-3">
            {(memory?.interests || []).length ? (
              (memory?.interests || []).map((interest) => (
                <span key={interest} className="pill">
                  {interest}
                </span>
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-white/12 px-4 py-3 text-sm text-white/52">
                No interests saved yet.
              </div>
            )}
          </div>
          <div className="mt-8 flex-1 space-y-3 overflow-y-auto pr-1">
            {(memory?.insights || []).map((insight) => (
              <div key={insight} className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm text-white/65">
                {insight}
              </div>
            ))}
          </div>
        </div>

        <div className="lux-panel flex h-full min-h-[520px] flex-col overflow-hidden p-6 sm:p-8">
          <SectionHeading
            eyebrow="Trip Timeline"
            title="Recent journeys and their strongest signal."
            body={memoryError ? `Memory warning: ${memoryError}` : "Use these memories to understand what the engine is optimizing for next."}
          />
          <div className="mt-8 flex flex-1 flex-col">
            {activeTrip ? (
              <>
                <div className="carousel-shell flex flex-1 flex-col justify-center px-0 sm:px-6">
                  <CarouselArrowButton
                    direction="left"
                    label="Show previous trip"
                    className="carousel-arrow-left"
                    onClick={showPreviousTrip}
                  />
                  <CarouselArrowButton
                    direction="right"
                    label="Show next trip"
                    className="carousel-arrow-right"
                    onClick={showNextTrip}
                  />
                  <AnimatePresence initial={false} custom={timelineDirection} mode="wait">
                    <motion.div
                      key={activeTrip.trip_id}
                      custom={timelineDirection}
                      variants={slideVariants}
                      initial="enter"
                      animate="center"
                      exit="exit"
                      transition={slideTransition}
                      className="flex flex-1"
                    >
                      <div className="grid flex-1 gap-4 rounded-lg border border-white/10 bg-black/25 p-5 md:grid-rows-[auto_1fr_auto]">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-white/10 font-display text-lg font-bold">
                            {String(timelineIndex + 1).padStart(2, "0")}
                          </div>
                          <div className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/45">
                            {deferredTrips.length} trips
                          </div>
                        </div>
                        <div className="min-w-0">
                          <p className="font-display text-3xl font-bold tracking-[-0.04em]">{activeTrip.destination}</p>
                          <p className="mt-2 text-sm text-white/55 capitalize">
                            {activeTrip.mood} mood | {activeTrip.days} days | {activeTrip.traveler_count === 1 ? "1 traveler" : `${activeTrip.traveler_count} travelers`} | {formatCurrency(activeTrip.budget, activeTrip.currency_code)}
                          </p>
                          <p className="mt-4 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-7 text-white/62">
                            {activeTrip.highlight}
                          </p>
                          <p className="mt-4 line-clamp-5 text-sm leading-7 text-white/60">{activeTrip.overview}</p>
                        </div>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="text-sm text-white/45">
                            Trip {timelineIndex + 1} of {deferredTrips.length}
                          </div>
                          <Link className="button-primary w-full sm:w-auto" to={`/trip/${activeTrip.trip_id}`}>
                            View Detail
                          </Link>
                        </div>
                      </div>
                    </motion.div>
                  </AnimatePresence>
                </div>
                <div className="mt-4 flex gap-2">
                  {deferredTrips.map((trip, index) => (
                    <button
                        key={trip.trip_id}
                        type="button"
                        aria-label={`Go to trip ${index + 1}`}
                        onClick={() => jumpToTrip(index)}
                        className={`h-2 flex-1 rounded-full transition ${
                          index === timelineIndex ? "bg-glow" : "bg-white/15 hover:bg-white/25"
                        }`}
                    />
                  ))}
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-white/12 p-6 text-sm text-white/55">
                No past trips yet. Generate your first plan to populate the timeline.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
