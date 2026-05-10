import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import CarouselArrowButton from "../components/ui/CarouselArrowButton";
import { getTripById } from "../lib/api";
import { formatCurrency } from "../lib/currency";
import { useAppContext } from "../state/AppContext";

function chunkItems(items, size) {
  const chunks = [];

  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }

  return chunks;
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

function TripDetailPage() {
  const { tripId } = useParams();
  const { memory, recentPlan, loadingMemory } = useAppContext();
  const [activeDayIndex, setActiveDayIndex] = useState(0);
  const [dayDirection, setDayDirection] = useState(1);
  const [localPlacesPage, setLocalPlacesPage] = useState(0);
  const [localPlacesDirection, setLocalPlacesDirection] = useState(1);
  const [fetchedTrip, setFetchedTrip] = useState(null);
  const [loadingTrip, setLoadingTrip] = useState(false);

  const cachedTrip = useMemo(() => {
    if (recentPlan?.trip_id === tripId) return recentPlan;
    return (memory?.past_trips || []).find((item) => item.trip_id === tripId);
  }, [memory, recentPlan, tripId]);
  const trip = cachedTrip || fetchedTrip;

  useEffect(() => {
    let cancelled = false;

    if (!tripId || cachedTrip) {
      setFetchedTrip(null);
      setLoadingTrip(false);
      return undefined;
    }

    setLoadingTrip(true);
    getTripById(tripId)
      .then((payload) => {
        if (!cancelled) {
          setFetchedTrip(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFetchedTrip(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingTrip(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [cachedTrip, tripId]);

  const itinerary = trip?.itinerary || [];
  const activeDay = itinerary[activeDayIndex] || null;
  const locations = useMemo(() => {
    if (!trip?.itinerary) return [];
    return trip.itinerary.flatMap((day) => day.activities.map((activity) => activity.location));
  }, [trip]);
  const routeStops = useMemo(() => Array.from(new Set(locations.filter(Boolean))).slice(0, 6), [locations]);
  const localPlacePages = useMemo(() => chunkItems(trip?.local_places || [], 4), [trip?.local_places]);
  const activeLocalPlaces = localPlacePages[localPlacesPage] || [];

  useEffect(() => {
    setActiveDayIndex(0);
    setLocalPlacesPage(0);
  }, [tripId]);

  useEffect(() => {
    if (!itinerary.length) {
      setActiveDayIndex(0);
      return;
    }

    if (activeDayIndex > itinerary.length - 1) {
      setActiveDayIndex(itinerary.length - 1);
    }
  }, [activeDayIndex, itinerary]);

  useEffect(() => {
    if (!localPlacePages.length) {
      setLocalPlacesPage(0);
      return;
    }

    if (localPlacesPage > localPlacePages.length - 1) {
      setLocalPlacesPage(localPlacePages.length - 1);
    }
  }, [localPlacePages, localPlacesPage]);

  const showPreviousDay = () => {
    setDayDirection(-1);
    setActiveDayIndex((current) => (current === 0 ? itinerary.length - 1 : current - 1));
  };

  const showNextDay = () => {
    setDayDirection(1);
    setActiveDayIndex((current) => (current + 1) % itinerary.length);
  };

  const jumpToDay = (index) => {
    if (index === activeDayIndex) return;
    setDayDirection(index > activeDayIndex ? 1 : -1);
    setActiveDayIndex(index);
  };

  const showPreviousLocalPlaces = () => {
    setLocalPlacesDirection(-1);
    setLocalPlacesPage((current) => (current === 0 ? localPlacePages.length - 1 : current - 1));
  };

  const showNextLocalPlaces = () => {
    setLocalPlacesDirection(1);
    setLocalPlacesPage((current) => (current + 1) % localPlacePages.length);
  };

  const jumpToLocalPlacesPage = (index) => {
    if (index === localPlacesPage) return;
    setLocalPlacesDirection(index > localPlacesPage ? 1 : -1);
    setLocalPlacesPage(index);
  };

  if (loadingMemory || loadingTrip) {
    return (
      <div className="page-shell">
        <div className="soft-panel p-10 text-center text-white/58">Loading trip detail...</div>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="page-shell">
        <div className="soft-panel p-10 text-center">
          <h1 className="font-display text-3xl font-bold tracking-[-0.05em]">Trip not found</h1>
          <p className="mt-4 text-white/58">Generate a plan first or return to the dashboard timeline.</p>
          <Link className="button-primary mt-6" to="/generator">
            Back to Generator
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <section className="lux-panel mx-auto max-w-[1040px] p-6 sm:p-8">
        <div className="grid gap-6">
          <div className="min-w-0">
            <p className="eyebrow">Info</p>
            <h1 className="mt-3 font-display text-4xl font-bold tracking-[-0.04em]">{trip.destination}</h1>
            <p className="mt-4 text-sm leading-7 text-white/62">{trip.overview}</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Mood</p>
              <p className="mt-2 font-display text-2xl font-bold capitalize">{trip.mood}</p>
            </div>
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Budget</p>
              <p className="mt-2 font-display text-2xl font-bold">{formatCurrency(trip.budget, trip.currency_code)}</p>
            </div>
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Trip Setup</p>
              <p className="mt-2 text-sm text-white/72">
                {trip.days} days for {trip.traveler_count === 1 ? "1 traveler" : `${trip.traveler_count} travelers`}
              </p>
            </div>
            <div className="soft-panel px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/45">Best Time</p>
              <p className="mt-2 text-sm text-white/72">{trip.best_time_to_visit}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="lux-panel mx-auto mt-6 max-w-[1040px] p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Route Activities</p>
            <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em]">Trip stages at a glance</h2>
          </div>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/45">
            {routeStops.length || 1} stops
          </span>
        </div>
        <div className="mt-6 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {(routeStops.length ? routeStops : ["Activities will appear after itinerary generation."]).map((location, index) => (
            <div key={`${location}-${index}`} className="rounded-lg border border-white/10 bg-black/25 px-4 py-4">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-glow/15 text-xs font-bold text-glow">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-white/42">Stage {index + 1}</p>
                  <p className="mt-1 text-sm font-medium text-white/80">{location}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-6 grid max-w-[1040px] items-stretch gap-6 xl:grid-cols-2">
        <div className="lux-panel flex min-h-[320px] flex-col p-6 sm:p-8">
          <p className="eyebrow">Cost Snapshot</p>
          <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em]">Budget breakdown</h2>
          <div className="mt-6 flex-1 space-y-3">
            {Object.entries(trip.cost_breakdown).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.04] px-4 py-4 text-sm">
                <span className="capitalize text-white/58">{key.replace("_", " ")}</span>
                <span className="font-semibold text-white">{formatCurrency(value, trip.currency_code)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lux-panel flex min-h-[320px] flex-col p-6 sm:p-8">
          <p className="eyebrow">Hotel Shortlist</p>
          <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em]">Stay options that fit</h2>
          <div className="mt-6 flex-1 overflow-y-auto pr-1">
            {trip.hotel_recommendations?.length ? (
              <div className="space-y-4">
                {trip.hotel_recommendations.map((hotel) => (
                  <div key={`${hotel.name}-${hotel.area}`} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-white">{hotel.name}</p>
                        <p className="mt-1 text-xs text-white/45">{hotel.area} | {hotel.category}</p>
                      </div>
                      <span className="text-xs font-semibold text-glow">
                        {formatCurrency(hotel.nightly_estimate, trip.currency_code)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-white/60">{hotel.why_it_fits}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-white/12 p-6 text-sm text-white/55">
                Hotel suggestions will appear here after itinerary generation.
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="mx-auto mt-6 max-w-[1040px]">
        {activeDay ? (
          <div className="lux-panel flex h-full flex-col p-6 sm:p-8">
            <div className="carousel-shell flex flex-1 flex-col justify-center px-0 sm:px-6">
              <CarouselArrowButton
                direction="left"
                label="Show previous day"
                className="carousel-arrow-left"
                onClick={showPreviousDay}
              />
              <CarouselArrowButton
                direction="right"
                label="Show next day"
                className="carousel-arrow-right"
                onClick={showNextDay}
              />
              <AnimatePresence initial={false} custom={dayDirection} mode="wait">
                <motion.div
                  key={activeDay.day}
                  custom={dayDirection}
                  variants={slideVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={slideTransition}
                  className="flex flex-1 flex-col"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex min-w-0 items-start gap-4">
                      <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-white/10 font-display text-xl font-bold">
                        {activeDay.day}
                      </div>
                      <div className="min-w-0">
                        <p className="eyebrow">Daywise Events</p>
                        <p className="mt-2 font-display text-3xl font-bold tracking-[-0.05em]">{activeDay.theme}</p>
                        <p className="mt-3 text-sm leading-7 text-white/60">{activeDay.summary}</p>
                      </div>
                    </div>
                    <span className="inline-flex min-w-[140px] self-start items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm font-semibold text-white">
                      {formatCurrency(activeDay.daily_estimate, trip.currency_code)} estimated
                    </span>
                  </div>

                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-white/45">Day Snapshot</p>
                      <div className="mt-3 grid gap-3 sm:grid-cols-3 md:grid-cols-1">
                        <div className="rounded-lg border border-white/8 bg-white/[0.04] px-3 py-3">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-white/42">Activities</p>
                          <p className="mt-1 font-display text-2xl font-bold text-white">{activeDay.activities.length}</p>
                        </div>
                        <div className="rounded-lg border border-white/8 bg-white/[0.04] px-3 py-3">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-white/42">Meals</p>
                          <p className="mt-1 font-display text-2xl font-bold text-white">{activeDay.meals?.length || 0}</p>
                        </div>
                        <div className="rounded-lg border border-white/8 bg-white/[0.04] px-3 py-3">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-white/42">Estimate</p>
                          <p className="mt-1 text-sm font-semibold text-white">
                            {formatCurrency(activeDay.daily_estimate, trip.currency_code)}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-white/45">Day Food Plan</p>
                      <div className="mt-3 space-y-2">
                        {activeDay.meals?.length ? (
                          activeDay.meals.map((meal) => {
                            const [label, ...detailParts] = meal.split(" - ");
                            const detail = detailParts.join(" - ");
                            return (
                              <div key={meal} className="rounded-lg border border-white/8 bg-black/20 px-3 py-3">
                                <p className="text-xs uppercase tracking-[0.2em] text-white/45">{label}</p>
                                <p className="mt-1 text-sm leading-6 text-white/72">{detail || label}</p>
                              </div>
                            );
                          })
                        ) : (
                          <div className="rounded-lg border border-dashed border-white/12 p-4 text-sm text-white/55">
                            No meal details saved for this day yet.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 rounded-lg border border-white/10 bg-black/20 p-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-white/45">Day Activities</p>
                      <p className="text-sm text-white/45">
                        Day {activeDayIndex + 1} of {itinerary.length}
                      </p>
                    </div>
                    <div className="mt-5 grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
                      {activeDay.activities.map((activity) => (
                        <motion.div
                          key={activity.title}
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="rounded-lg border border-white/10 bg-white/[0.04] p-4"
                        >
                          <div className="flex h-full flex-col gap-3">
                            <div className="min-w-0 flex-1">
                              <p className="text-xs uppercase tracking-[0.24em] text-white/45">{activity.time}</p>
                              <p className="mt-2 font-semibold text-white">{activity.title}</p>
                              <p className="mt-2 text-sm text-white/55">{activity.location}</p>
                              <p className="mt-3 text-sm leading-7 text-white/60">{activity.description}</p>
                            </div>
                            <span className="pill self-start">
                              {formatCurrency(activity.estimated_cost, trip.currency_code)}
                            </span>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>

            <div className="mt-4 flex gap-2">
              {itinerary.map((day, index) => (
                <button
                  key={day.day}
                  type="button"
                  aria-label={`Go to day ${day.day}`}
                  onClick={() => jumpToDay(index)}
                  className={`h-2 flex-1 rounded-full transition ${
                    index === activeDayIndex ? "bg-glow" : "bg-white/15 hover:bg-white/25"
                  }`}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="soft-panel p-8 text-white/58">This saved trip has summary memory but no detailed day cards yet.</div>
        )}
      </section>

      {localPlacePages.length ? (
        <section className="lux-panel mx-auto mt-6 max-w-[1040px] p-6 sm:p-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Local Accuracy Picks</p>
              <h2 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em]">On-the-ground spot suggestions</h2>
            </div>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/45">
              {trip.local_places.length} picks
            </span>
          </div>

          <div className="carousel-shell mt-6 px-0 sm:px-6">
            <CarouselArrowButton
              direction="left"
              label="Show previous local picks"
              className="carousel-arrow-left"
              onClick={showPreviousLocalPlaces}
            />
            <CarouselArrowButton
              direction="right"
              label="Show next local picks"
              className="carousel-arrow-right"
              onClick={showNextLocalPlaces}
            />
            <AnimatePresence initial={false} custom={localPlacesDirection} mode="wait">
              <motion.div
                key={`local-page-${localPlacesPage}`}
                custom={localPlacesDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={slideTransition}
                className="grid gap-4 md:grid-cols-2"
              >
                {activeLocalPlaces.map((place) => (
                  <div key={`${place.name}-${place.area}`} className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-white">{place.name}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.16em] text-white/42">
                          {place.area} | {place.place_type}
                        </p>
                      </div>
                      <span className="pill h-fit">{place.best_time}</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-white/58">{place.why_go}</p>
                  </div>
                ))}
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="mt-4 flex gap-2">
            {localPlacePages.map((page, index) => (
              <button
                key={`local-page-${page[0]?.name || index}`}
                type="button"
                aria-label={`Go to local picks page ${index + 1}`}
                onClick={() => jumpToLocalPlacesPage(index)}
                className={`h-2 flex-1 rounded-full transition ${
                  index === localPlacesPage ? "bg-glow" : "bg-white/15 hover:bg-white/25"
                }`}
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

export default TripDetailPage;
