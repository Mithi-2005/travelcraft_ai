import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import MagneticButton from "../components/ui/MagneticButton";
import { PlanSkeleton } from "../components/ui/LoadingSkeleton";
import { getDestinationSuggestions } from "../lib/api";
import { APP_CURRENCY_CODE, formatCurrency } from "../lib/currency";
import { useAppContext } from "../state/AppContext";

const RECENT_DESTINATIONS_KEY = "travelcraft_recent_destinations";

const popularDestinations = [
  {
    id: "goa-india",
    display_name: "Goa, India",
    region: "Konkan Coast",
    country: "India",
    description: "Relaxed beach pacing, boutique stays, and easy coastal planning.",
    highlights: ["beaches", "nightlife", "slow travel"],
  },
  {
    id: "jaipur-india",
    display_name: "Jaipur, India",
    region: "Rajasthan",
    country: "India",
    description: "Bold heritage texture, palace hotels, and culture-rich city energy.",
    highlights: ["heritage", "shopping", "architecture"],
  },
  {
    id: "tokyo-japan",
    display_name: "Tokyo, Japan",
    region: "Kanto",
    country: "Japan",
    description: "High-design city breaks with standout food, neighborhoods, and late-night energy.",
    highlights: ["food", "design", "nightlife"],
  },
  {
    id: "lisbon-portugal",
    display_name: "Lisbon, Portugal",
    region: "Lisbon District",
    country: "Portugal",
    description: "Sunlit streets, riverside pacing, and strong value for culture-first trips.",
    highlights: ["architecture", "food", "walking city"],
  },
];

const defaultInterests = [
  "food",
  "architecture",
  "wellness",
  "nightlife",
  "art",
  "nature",
  "shopping",
  "hidden gems",
];

const destinationInterestSets = [
  {
    match: ["tirumala", "tirupati", "temple", "varanasi", "rishikesh"],
    interests: ["pilgrimage", "temples", "prasadam", "spiritual walks", "family", "local food", "nature", "culture"],
  },
  {
    match: ["goa", "bali", "beach", "maldives", "phuket"],
    interests: ["beaches", "seafood", "nightlife", "water sports", "wellness", "sunsets", "cafes", "slow travel"],
  },
  {
    match: ["jaipur", "udaipur", "delhi", "agra", "rome", "kyoto"],
    interests: ["heritage", "architecture", "markets", "museums", "local food", "photography", "crafts", "culture"],
  },
  {
    match: ["manali", "leh", "ladakh", "himachal", "mountain"],
    interests: ["mountains", "adventure", "nature", "cafes", "viewpoints", "road trips", "treks", "local food"],
  },
];

function getDestinationInterests(destination) {
  const normalized = destination.toLowerCase();
  const matched = destinationInterestSets.find((set) => set.match.some((term) => normalized.includes(term)));
  return matched?.interests || defaultInterests;
}

const moods = [
  { id: "relaxed", label: "Relaxed", copy: "Slow mornings, fewer transitions, restorative pacing." },
  { id: "adventure", label: "Adventure", copy: "More movement, high-energy highlights, bold activity mix." },
  { id: "luxury", label: "Luxury", copy: "Elevated stays, signature dining, polished service moments." },
];

function formatInsight(insight) {
  if (!insight) return "";
  const parts = insight.split(": ");
  if (parts.length < 2) return insight;
  return parts.slice(1).join(": ");
}

function buildLiveDefaultForm(memory) {
  return {
    destination: "",
    days: 4,
    arrival_time: "10:00",
    traveler_count: 1,
    budget: memory?.budget_preference ?? "",
    currency_code: APP_CURRENCY_CODE,
    interests: memory?.interests || [],
    mood: memory?.preferred_mood || "relaxed",
    pace: "balanced",
    accommodation_style: "mixed",
    food_preference: "local favorites",
    must_include: "",
    avoid: "",
  };
}

function validateForm(form) {
  const nextErrors = {};
  const trimmedDestination = form.destination.trim();
  const numericDays = Number(form.days);
  const numericTravelerCount = Number(form.traveler_count);
  const numericBudget = Number(form.budget);
  const selectedInterests = (form.interests || []).filter(Boolean);

  if (!trimmedDestination) {
    nextErrors.destination = "Enter a destination to generate a trip.";
  }

  if (!Number.isFinite(numericBudget) || numericBudget <= 0) {
    nextErrors.budget = "Budget must be greater than 0.";
  }

  if (!Number.isInteger(numericDays) || numericDays <= 0) {
    nextErrors.days = "Trip length must be at least 1 day.";
  }

  if (!Number.isInteger(numericTravelerCount) || numericTravelerCount <= 0) {
    nextErrors.traveler_count = "Traveler count must be at least 1.";
  }

  if (!selectedInterests.length) {
    nextErrors.interests = "Select at least one interest so the plan has something specific to optimize for.";
  }

  return nextErrors;
}

function loadRecentDestinations() {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_DESTINATIONS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveRecentDestinations(destinations) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(RECENT_DESTINATIONS_KEY, JSON.stringify(destinations.slice(0, 5)));
}

function TripGeneratorPage() {
  const { createTrip, isGenerating, recentPlan, memory } = useAppContext();
  const [form, setForm] = useState(() => buildLiveDefaultForm(null));
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [hasEditedForm, setHasEditedForm] = useState(false);
  const [destinationSuggestions, setDestinationSuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(-1);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [recentDestinations, setRecentDestinations] = useState(() => loadRecentDestinations());
  const [destinationFocused, setDestinationFocused] = useState(false);
  const [refineInstruction, setRefineInstruction] = useState("");
  const destinationFieldRef = useRef(null);

  const activePlan = useMemo(() => plan || recentPlan, [plan, recentPlan]);
  const suggestedInterests = useMemo(() => getDestinationInterests(form.destination), [form.destination]);
  const serviceBadges = useMemo(
    () =>
      activePlan
        ? [
            {
              label: "Research",
              mode: activePlan.research_mode,
              error: activePlan.research_error,
            },
            {
              label: "LLM",
              mode: activePlan.llm_mode,
              error: activePlan.llm_error,
            },
          ]
        : [],
    [activePlan],
  );

  const travelerLabel = useMemo(() => {
    if (!activePlan?.traveler_count) return "";
    return activePlan.traveler_count === 1 ? "1 traveler" : `${activePlan.traveler_count} travelers`;
  }, [activePlan]);

  useEffect(() => {
    if (hasEditedForm) return;
    setForm(buildLiveDefaultForm(memory));
  }, [memory, hasEditedForm]);

  useEffect(() => {
    const handlePointerDown = (event) => {
      if (destinationFieldRef.current && !destinationFieldRef.current.contains(event.target)) {
        setSuggestionsOpen(false);
        setActiveSuggestionIndex(-1);
        setDestinationFocused(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  useEffect(() => {
    const trimmedQuery = form.destination.trim();
    if (selectedSuggestion && trimmedQuery !== selectedSuggestion.display_name) {
      setSelectedSuggestion(null);
    }

    if (selectedSuggestion && trimmedQuery === selectedSuggestion.display_name) {
      setDestinationSuggestions([]);
      setSuggestionsLoading(false);
      setSuggestionsOpen(false);
      setActiveSuggestionIndex(-1);
      return undefined;
    }

    if (trimmedQuery.length < 2) {
      setDestinationSuggestions([]);
      setSuggestionsLoading(false);
      setSuggestionsOpen(destinationFocused);
      setActiveSuggestionIndex(-1);
      return undefined;
    }

    let cancelled = false;
    setSuggestionsLoading(true);

    const timer = setTimeout(async () => {
      try {
        const results = await getDestinationSuggestions(trimmedQuery, 6);
        if (cancelled) return;
        setDestinationSuggestions(results);
        setSuggestionsOpen(true);
        setActiveSuggestionIndex(results.length ? 0 : -1);
      } catch {
        if (cancelled) return;
        setDestinationSuggestions([]);
        setSuggestionsOpen(false);
        setActiveSuggestionIndex(-1);
      } finally {
        if (!cancelled) {
          setSuggestionsLoading(false);
        }
      }
    }, 180);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [destinationFocused, form.destination, selectedSuggestion]);

  const toggleInterest = (interest) => {
    setHasEditedForm(true);
    setForm((current) => ({
      ...current,
      interests: current.interests.includes(interest)
        ? current.interests.filter((item) => item !== interest)
        : [...current.interests, interest],
    }));
  };

  const handleDestinationSelect = (suggestion) => {
    setHasEditedForm(true);
    setSelectedSuggestion(suggestion);
    setForm((current) => ({ ...current, destination: suggestion.display_name }));
    setFieldErrors((current) => ({ ...current, destination: "" }));
    setSuggestionsOpen(false);
    setActiveSuggestionIndex(-1);
    setDestinationFocused(false);
    const nextRecent = [
      suggestion,
      ...recentDestinations.filter((item) => item.display_name !== suggestion.display_name),
    ].slice(0, 5);
    setRecentDestinations(nextRecent);
    saveRecentDestinations(nextRecent);
  };

  const handleDestinationKeyDown = (event) => {
    if (!suggestionsOpen || !destinationSuggestions.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestionIndex((current) => (current + 1) % destinationSuggestions.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestionIndex((current) =>
        current <= 0 ? destinationSuggestions.length - 1 : current - 1,
      );
      return;
    }

    if (event.key === "Enter" && activeSuggestionIndex >= 0) {
      event.preventDefault();
      handleDestinationSelect(destinationSuggestions[activeSuggestionIndex]);
      return;
    }

    if (event.key === "Escape") {
      setSuggestionsOpen(false);
      setActiveSuggestionIndex(-1);
    }
  };

  const buildRequestPayload = (extraInstruction = "") => ({
    ...form,
    destination: form.destination.trim(),
    days: Number(form.days),
    traveler_count: Number(form.traveler_count),
    budget: Number(form.budget),
    must_include: [
      ...form.must_include
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      ...(extraInstruction ? [`Refine the plan: ${extraInstruction}`] : []),
    ],
    avoid: form.avoid
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  });

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    const nextErrors = validateForm(form);
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      return;
    }
    try {
      const result = await createTrip(buildRequestPayload());
      const manualDestination = {
        id: `manual-${form.destination.trim().toLowerCase().replace(/\s+/g, "-")}`,
        display_name: form.destination.trim(),
        region: selectedSuggestion?.region || "",
        country: selectedSuggestion?.country || "",
        description:
          selectedSuggestion?.description || "A recently used destination from your own planning history.",
        highlights: selectedSuggestion?.highlights || ["recent", "saved"],
      };
      const nextRecent = [
        manualDestination,
        ...recentDestinations.filter((item) => item.display_name !== manualDestination.display_name),
      ].slice(0, 5);
      setRecentDestinations(nextRecent);
      saveRecentDestinations(nextRecent);
      setPlan(result);
    } catch (submitError) {
      setError(submitError.message || "Unable to generate a trip right now.");
    }
  };

  const handleRefinePlan = async () => {
    const instruction = refineInstruction.trim();
    if (!instruction || !activePlan) return;
    setError("");
    try {
      const result = await createTrip(buildRequestPayload(instruction));
      setPlan(result);
      setRefineInstruction("");
    } catch (submitError) {
      setError(submitError.message || "Unable to refine this trip right now.");
    }
  };

  return (
    <div className="page-shell">
      <section className="page-stack">
        <form onSubmit={handleSubmit} className="lux-panel p-6 sm:p-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="eyebrow">Trip Generator</p>
              <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.04em] sm:text-4xl">
                Compose a new journey.
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/60">
                Set the essentials once. The planner combines live destination data, AI itinerary design, and your saved memory.
              </p>
            </div>
            <div className="section-card max-w-sm text-sm leading-6 text-white/58">
              Budget is handled in INR. Saved interests and mood prefill when memory is available.
            </div>
          </div>

          <div className="form-layout mt-8">
            <div ref={destinationFieldRef} className="field-full relative">
              <label htmlFor="trip-destination" className="field-label">
                Destination
              </label>
              <input
                id="trip-destination"
                className="input-shell"
                value={form.destination}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setFieldErrors((current) => ({ ...current, destination: "" }));
                  if (selectedSuggestion && event.target.value !== selectedSuggestion.display_name) {
                    setSelectedSuggestion(null);
                  }
                  setForm((current) => ({ ...current, destination: event.target.value }));
                }}
                onFocus={() => {
                  setDestinationFocused(true);
                  setSuggestionsOpen(
                    !(selectedSuggestion && form.destination.trim() === selectedSuggestion.display_name),
                  );
                }}
                onKeyDown={handleDestinationKeyDown}
                placeholder="Start typing a city or destination"
                autoComplete="off"
                aria-autocomplete="list"
                aria-controls="destination-suggestion-list"
                aria-expanded={suggestionsOpen}
                aria-activedescendant={
                  activeSuggestionIndex >= 0
                    ? `destination-suggestion-${destinationSuggestions[activeSuggestionIndex]?.id}`
                    : undefined
                }
              />
              <p className="mt-2 text-xs text-white/42">Type 2+ characters for destination suggestions.</p>

              {suggestionsLoading ? (
                <div className="mt-3 rounded-lg border border-white/10 bg-black/25 px-4 py-3 text-sm text-white/58">
                  Searching destinations...
                </div>
              ) : null}

              {suggestionsOpen && form.destination.trim().length < 2 ? (
                <div className="absolute z-30 mt-3 w-full rounded-lg border border-white/10 bg-[#0b1118]/95 p-4 shadow-[0_28px_70px_rgba(0,0,0,0.4)] backdrop-blur-2xl">
                  {recentDestinations.length ? (
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-white/42">Recent Searches</p>
                      <div className="mt-3 grid gap-2">
                        {recentDestinations.map((suggestion) => (
                          <button
                            key={`recent-${suggestion.id}`}
                            type="button"
                            onMouseDown={(event) => {
                              event.preventDefault();
                              handleDestinationSelect(suggestion);
                            }}
                            className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-left transition hover:bg-white/[0.08]"
                          >
                            <p className="font-semibold text-white">{suggestion.display_name}</p>
                            <p className="mt-1 text-sm text-white/55">{suggestion.description}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <div className={recentDestinations.length ? "mt-4 border-t border-white/10 pt-4" : ""}>
                    <p className="text-xs uppercase tracking-[0.24em] text-white/42">Popular Destinations</p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      {popularDestinations.map((suggestion) => (
                        <button
                          key={`popular-${suggestion.id}`}
                          type="button"
                          onMouseDown={(event) => {
                            event.preventDefault();
                            handleDestinationSelect(suggestion);
                          }}
                          className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-left transition hover:bg-white/[0.08]"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-display text-lg font-bold tracking-[-0.03em] text-white">
                                {suggestion.display_name}
                              </p>
                              <p className="mt-1 text-xs uppercase tracking-[0.18em] text-white/42">
                                {suggestion.region}
                              </p>
                            </div>
                            <span className="pill bg-black/20 text-[10px]">{suggestion.country}</span>
                          </div>
                          <p className="mt-3 text-sm leading-7 text-white/60">{suggestion.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : null}

              {suggestionsOpen && destinationSuggestions.length ? (
                <div
                  id="destination-suggestion-list"
                  role="listbox"
                  className="absolute z-30 mt-3 max-h-[360px] w-full overflow-y-auto rounded-lg border border-white/10 bg-[#0b1118]/95 p-3 shadow-[0_28px_70px_rgba(0,0,0,0.4)] backdrop-blur-2xl"
                >
                  <div className="space-y-2">
                    {destinationSuggestions.map((suggestion, index) => {
                      const isActive = index === activeSuggestionIndex;
                      return (
                        <button
                          key={suggestion.id}
                          id={`destination-suggestion-${suggestion.id}`}
                          type="button"
                          role="option"
                          aria-selected={isActive}
                          onMouseDown={(event) => {
                            event.preventDefault();
                            handleDestinationSelect(suggestion);
                          }}
                          className={`w-full rounded-lg border p-4 text-left transition ${
                            isActive
                              ? "border-glow/45 bg-glow/10 shadow-[0_18px_40px_rgba(103,246,215,0.08)]"
                              : "border-white/10 bg-white/[0.04] hover:bg-white/[0.08]"
                          }`}
                        >
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="font-display text-xl font-bold tracking-[-0.04em] text-white">
                                {suggestion.display_name}
                              </p>
                              <p className="mt-1 text-xs uppercase tracking-[0.2em] text-white/42">
                                {suggestion.region}
                              </p>
                            </div>
                            <span className="pill bg-black/25 text-[10px]">{suggestion.country}</span>
                          </div>
                          <p className="mt-3 text-sm leading-7 text-white/62">{suggestion.description}</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {suggestion.highlights.map((highlight) => (
                              <span key={highlight} className="pill bg-white/[0.03] text-[10px] uppercase tracking-[0.14em]">
                                {highlight}
                              </span>
                            ))}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {!suggestionsLoading && suggestionsOpen && form.destination.trim().length >= 2 && !destinationSuggestions.length ? (
                <div className="absolute z-30 mt-3 w-full rounded-lg border border-white/10 bg-[#0b1118]/95 p-4 text-sm text-white/56 shadow-[0_24px_60px_rgba(0,0,0,0.35)] backdrop-blur-2xl">
                  No close matches found. Try a city name, country, or a more specific search.
                </div>
              ) : null}

              {selectedSuggestion ? (
                <div className="mt-4 rounded-lg border border-white/10 bg-black/25 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.24em] text-white/42">Selected Destination</p>
                      <p className="mt-2 font-display text-2xl font-bold tracking-[-0.04em] text-white">
                        {selectedSuggestion.display_name}
                      </p>
                    </div>
                    <span className="pill bg-white/[0.04]">{selectedSuggestion.region}</span>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-white/62">{selectedSuggestion.description}</p>
                </div>
              ) : null}

              {fieldErrors.destination ? (
                <p className="mt-2 text-sm text-coral">{fieldErrors.destination}</p>
              ) : null}
            </div>

            <div>
              <label htmlFor="trip-days" className="field-label">
                Number of Days
              </label>
              <input
                id="trip-days"
                className="input-shell"
                type="number"
                min="1"
                step="1"
                value={form.days}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setFieldErrors((current) => ({ ...current, days: "" }));
                  setForm((current) => ({ ...current, days: event.target.value }));
                }}
              />
              <p className="mt-2 text-xs text-white/42">How many days to generate.</p>
              {fieldErrors.days ? <p className="mt-2 text-sm text-coral">{fieldErrors.days}</p> : null}
            </div>

            <div>
              <label htmlFor="trip-arrival-time" className="field-label">
                Arrival Time
              </label>
              <input
                id="trip-arrival-time"
                className="input-shell"
                type="time"
                value={form.arrival_time}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setForm((current) => ({ ...current, arrival_time: event.target.value }));
                }}
              />
              <p className="mt-2 text-xs text-white/42">When you reach the destination.</p>
            </div>

            <div>
              <label htmlFor="trip-travelers" className="field-label">
                Number of Persons
              </label>
              <input
                id="trip-travelers"
                className="input-shell"
                type="number"
                min="1"
                step="1"
                value={form.traveler_count}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setFieldErrors((current) => ({ ...current, traveler_count: "" }));
                  setForm((current) => ({ ...current, traveler_count: event.target.value }));
                }}
              />
              <p className="mt-2 text-xs text-white/42">Used for pacing, stays, and budget realism.</p>
              {fieldErrors.traveler_count ? (
                <p className="mt-2 text-sm text-coral">{fieldErrors.traveler_count}</p>
              ) : null}
            </div>

            <div>
              <label htmlFor="trip-budget" className="field-label">
                Budget (INR)
              </label>
              <input
                id="trip-budget"
                className="input-shell"
                type="number"
                min="0.01"
                step="0.01"
                value={form.budget}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setFieldErrors((current) => ({ ...current, budget: "" }));
                  setForm((current) => ({ ...current, budget: event.target.value, currency_code: APP_CURRENCY_CODE }));
                }}
              />
              <p className="mt-2 text-xs text-white/42">Enter the total trip budget you want the itinerary to respect.</p>
              {fieldErrors.budget ? (
                <p className="mt-2 text-sm text-coral">{fieldErrors.budget}</p>
              ) : null}
            </div>

            <div className="field-full">
              <label className="field-label">Trip Mood</label>
              <div className="grid gap-3 lg:grid-cols-3">
                {moods.map((mood) => (
                  <button
                    key={mood.id}
                    type="button"
                    data-cursor="active"
                    onClick={() => {
                      setHasEditedForm(true);
                      setFieldErrors((current) => ({ ...current, mood: "" }));
                      setForm((current) => ({ ...current, mood: mood.id }));
                    }}
                    className={`h-full rounded-lg border p-4 text-left transition ${
                      form.mood === mood.id
                        ? "border-glow/70 bg-glow/10 shadow-[0_20px_45px_rgba(103,246,215,0.08)]"
                        : "border-white/10 bg-white/[0.04] hover:bg-white/[0.07]"
                    }`}
                  >
                    <p className="font-display text-xl font-bold">{mood.label}</p>
                    <p className="mt-2 text-sm text-white/58">{mood.copy}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="trip-pace" className="field-label">
                Pace
              </label>
              <select
                id="trip-pace"
                className="input-shell select-shell"
                value={form.pace}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setForm((current) => ({ ...current, pace: event.target.value }));
                }}
              >
                <option value="slow">Slow</option>
                <option value="balanced">Balanced</option>
                <option value="packed">Packed</option>
              </select>
            </div>

            <div>
              <label htmlFor="trip-stay-style" className="field-label">
                Stay Style
              </label>
              <select
                id="trip-stay-style"
                className="input-shell select-shell"
                value={form.accommodation_style}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setForm((current) => ({ ...current, accommodation_style: event.target.value }));
                }}
              >
                <option value="mixed">Mixed</option>
                <option value="budget hotel">Budget hotel</option>
                <option value="boutique hotel">Boutique hotel</option>
                <option value="luxury hotel">Luxury hotel</option>
                <option value="serviced apartment">Serviced apartment</option>
              </select>
            </div>

            <div>
              <label htmlFor="trip-food" className="field-label">
                Food Preference
              </label>
              <input
                id="trip-food"
                className="input-shell"
                value={form.food_preference}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setForm((current) => ({ ...current, food_preference: event.target.value }));
                }}
                placeholder="street food, cafes, vegetarian, fine dining"
              />
            </div>

            <div>
              <label htmlFor="trip-must-include" className="field-label">
                Must Include
              </label>
              <input
                id="trip-must-include"
                className="input-shell"
                value={form.must_include}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setForm((current) => ({ ...current, must_include: event.target.value }));
                }}
                placeholder="sunset view, museum, spa"
              />
            </div>

            <div className="field-full">
              <label htmlFor="trip-avoid" className="field-label">
                Avoid
              </label>
              <input
                id="trip-avoid"
                className="input-shell"
                value={form.avoid}
                onChange={(event) => {
                  setHasEditedForm(true);
                  setForm((current) => ({ ...current, avoid: event.target.value }));
                }}
                placeholder="long drives, crowded clubs, early mornings"
              />
            </div>

            <div className="field-full">
              <label className="field-label">Interests Based On Destination</label>
              <div className="flex flex-wrap gap-3">
                {suggestedInterests.map((interest) => {
                  const selected = form.interests.includes(interest);
                  return (
                    <button
                      key={interest}
                      type="button"
                      data-cursor="active"
                      onClick={() => toggleInterest(interest)}
                      className={`rounded-full border px-4 py-2 text-sm transition ${
                        selected
                          ? "border-coral/60 bg-coral/12 text-white"
                          : "border-white/10 bg-white/[0.04] text-white/68 hover:bg-white/[0.08]"
                      }`}
                    >
                      {interest}
                    </button>
                  );
                })}
              </div>
              {fieldErrors.interests ? (
                <p className="mt-2 text-sm text-coral">{fieldErrors.interests}</p>
              ) : null}
            </div>

            {error ? (
              <div className="rounded-lg border border-coral/30 bg-coral/8 p-4 text-sm text-coral">{error}</div>
            ) : null}

            <div className="field-full flex justify-end">
              <MagneticButton type="submit" className="button-primary w-full sm:w-auto">
                {isGenerating ? "Generating itinerary..." : "Generate Trip"}
              </MagneticButton>
            </div>
          </div>
        </form>

        <div className="space-y-6">
          {isGenerating ? (
            <PlanSkeleton />
          ) : activePlan ? (
            <>
              <div className="lux-panel p-8">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="eyebrow">Generated Plan</p>
                    <h2 className="mt-3 font-display text-4xl font-bold tracking-[-0.055em]">
                      {activePlan.destination}
                    </h2>
                    <p className="mt-4 max-w-3xl text-sm leading-8 text-white/63">{activePlan.overview}</p>
                  </div>
                  <div className="section-card min-w-[180px]">
                    <p className="text-xs uppercase tracking-[0.24em] text-white/45">Best Time</p>
                    <p className="mt-2 text-sm leading-7 text-white/72">{activePlan.best_time_to_visit}</p>
                  </div>
                </div>
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-white/42">Trip Length</p>
                    <p className="mt-2 font-display text-2xl font-bold text-white">{activePlan.days} days</p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-white/42">Travel Party</p>
                    <p className="mt-2 font-display text-2xl font-bold text-white">{travelerLabel}</p>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-white/42">Trip Budget</p>
                    <p className="mt-2 font-display text-2xl font-bold text-white">
                      {formatCurrency(activePlan.budget, activePlan.currency_code)}
                    </p>
                  </div>
                </div>
                <div className="mt-6 grid gap-3 md:grid-cols-2">
                  {serviceBadges.map((service) => {
                    const live = service.mode === "live";
                    return (
                      <div
                        key={service.label}
                        className={`rounded-lg border p-4 ${
                          live ? "border-glow/30 bg-glow/10" : "border-coral/30 bg-coral/10"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs uppercase tracking-[0.24em] text-white/45">{service.label}</p>
                          <span
                            className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
                              live ? "bg-glow/20 text-glow" : "bg-coral/20 text-coral"
                            }`}
                          >
                            {service.mode}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-white/66">
                          {live
                            ? `${service.label} used live API data successfully.`
                            : `${service.label} fell back to the local template path.`}
                        </p>
                        {service.error ? <p className="mt-2 text-xs leading-6 text-white/52">{service.error}</p> : null}
                      </div>
                    );
                  })}
                </div>
                <div className="mt-6 grid gap-3 lg:grid-cols-3">
                  {activePlan.live_insights.map((insight, index) => (
                    <div key={insight} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                      <p className="text-xs uppercase tracking-[0.24em] text-white/42">Signal 0{index + 1}</p>
                      <p className="mt-3 text-sm leading-7 text-white/66">{formatInsight(insight)}</p>
                    </div>
                  ))}
                </div>
                {activePlan.research_sources?.length ? (
                  <div className="mt-6 rounded-lg border border-white/10 bg-black/20 p-5 sm:p-6">
                    <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-[0.24em] text-white/45">Research Sources</p>
                        <p className="mt-2 text-sm text-white/58">
                          These are the live web sources currently shaping destination context.
                        </p>
                      </div>
                      <div className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-white/46">
                        {activePlan.research_sources.length} sources
                      </div>
                    </div>
                    <div className="mt-5 grid gap-4 xl:grid-cols-2">
                      {activePlan.research_sources.map((source) => (
                        <a
                          key={`${source.title}-${source.url}`}
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="group block rounded-lg border border-white/8 bg-white/[0.04] p-5 transition hover:border-glow/30 hover:bg-white/[0.08]"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <p className="text-xs uppercase tracking-[0.24em] text-white/42">{source.domain || "source"}</p>
                              <p className="mt-3 font-display text-2xl font-bold tracking-[-0.04em] text-white/92">
                                {source.title}
                              </p>
                            </div>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-white/45 transition group-hover:border-glow/30 group-hover:text-glow">
                              Open
                            </span>
                          </div>
                          {source.snippet ? <p className="mt-4 text-sm leading-7 text-white/62">{source.snippet}</p> : null}
                        </a>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="soft-panel p-6 sm:p-7">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="eyebrow">Customize More</p>
                    <h3 className="mt-3 font-display text-2xl font-bold tracking-[-0.04em]">Ask AI to refine this plan</h3>
                  </div>
                  <button
                    type="button"
                    className="button-primary w-full lg:w-auto"
                    onClick={handleRefinePlan}
                    disabled={isGenerating || !refineInstruction.trim()}
                  >
                    {isGenerating ? "Refining..." : "Refine Plan"}
                  </button>
                </div>
                <textarea
                  className="input-shell mt-5 min-h-[92px]"
                  value={refineInstruction}
                  onChange={(event) => setRefineInstruction(event.target.value)}
                  placeholder="Example: make it slower, add more temple time, avoid long drives, add better hotels"
                />
              </div>

              {(activePlan.hotel_recommendations?.length || activePlan.local_places?.length) ? (
                <div className="grid items-stretch gap-6 lg:grid-cols-[1fr_1fr]">
                  {activePlan.hotel_recommendations?.length ? (
                    <div className="soft-panel flex h-full min-h-[480px] flex-col p-6 sm:p-7">
                      <p className="eyebrow">Hotel Shortlist</p>
                      <div className="mt-5 flex-1 space-y-4 overflow-y-auto pr-1">
                        {activePlan.hotel_recommendations.map((hotel) => (
                          <div key={`${hotel.name}-${hotel.area}`} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="font-display text-xl font-bold tracking-[-0.04em]">{hotel.name}</p>
                                <p className="mt-1 text-sm text-white/50">{hotel.area} | {hotel.category}</p>
                              </div>
                              <span className="pill whitespace-nowrap">
                                {formatCurrency(hotel.nightly_estimate, activePlan.currency_code)}/night
                              </span>
                            </div>
                            <p className="mt-3 text-sm leading-7 text-white/62">{hotel.why_it_fits}</p>
                            {hotel.booking_tip ? <p className="mt-2 text-xs text-white/45">{hotel.booking_tip}</p> : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {activePlan.local_places?.length ? (
                    <div className="soft-panel flex h-full min-h-[480px] flex-col p-6 sm:p-7">
                      <p className="eyebrow">Accurate Local Picks</p>
                      <div className="mt-5 space-y-3">
                        {activePlan.local_places.map((place) => (
                          <div key={`${place.name}-${place.area}`} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="font-semibold text-white">{place.name}</p>
                                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-white/42">{place.area} | {place.place_type}</p>
                              </div>
                              <span className="text-xs text-white/45">{place.best_time}</span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-white/62">{place.why_go}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}

              <div className="grid items-stretch gap-6 xl:grid-cols-2">
                <div className="soft-panel flex h-full flex-col p-6 sm:p-7">
                  <p className="eyebrow">Featured Attractions</p>
                  <div className="mt-5 space-y-4">
                    {activePlan.attractions.map((item) => (
                      <div key={item.name} className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="font-display text-2xl font-bold tracking-[-0.05em]">{item.name}</p>
                            <p className="mt-2 text-sm leading-7 text-white/60">{item.reason}</p>
                          </div>
                          <span className="pill whitespace-nowrap">
                            {formatCurrency(item.estimated_cost, activePlan.currency_code)}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-white/45">Best time: {item.best_time}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="soft-panel flex h-full flex-col p-6 sm:p-7">
                  <p className="eyebrow">Estimated Costs</p>
                  <div className="mt-6 grid gap-3">
                    {Object.entries(activePlan.cost_breakdown).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between rounded-lg border border-white/8 bg-black/20 px-4 py-3">
                        <span className="capitalize text-white/65">{key.replace("_", " ")}</span>
                        <span className="font-semibold text-white">{formatCurrency(value, activePlan.currency_code)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="soft-panel flex h-full flex-col p-6 sm:p-7">
                  <p className="eyebrow">Smart Suggestions</p>
                  <div className="mt-4 space-y-3">
                    {activePlan.smart_suggestions.map((item) => (
                      <div key={item.title} className="rounded-lg border border-white/8 bg-white/[0.04] p-4">
                        <p className="font-semibold text-white">{item.title}</p>
                        <p className="mt-2 text-sm text-white/60">{item.description}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="soft-panel flex h-full flex-col p-6 sm:p-7">
                  <p className="eyebrow">Logistics</p>
                  {activePlan.logistics ? (
                    <div className="mt-4 space-y-3 rounded-lg border border-white/10 bg-black/20 p-5 text-sm leading-6 text-white/62">
                      <p><span className="font-semibold text-white/80">Base:</span> {activePlan.logistics.neighborhood_base}</p>
                      <p><span className="font-semibold text-white/80">Arrival:</span> {activePlan.logistics.arrival_transfer}</p>
                      <p><span className="font-semibold text-white/80">Transport:</span> {activePlan.logistics.local_transport}</p>
                    </div>
                  ) : (
                    <div className="mt-4 rounded-lg border border-dashed border-white/12 p-5 text-sm text-white/55">
                      Logistics details are not available for this plan yet.
                    </div>
                  )}
                </div>
              </div>

              <div className="lux-panel p-8">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="eyebrow">Day-wise Itinerary</p>
                    <h3 className="mt-3 font-display text-3xl font-bold tracking-[-0.055em]">Animated travel timeline</h3>
                  </div>
                  <Link className="button-secondary" to={`/trip/${activePlan.trip_id}`}>
                    Open Detail View
                  </Link>
                </div>
                <div className="mt-8 space-y-4">
                  {activePlan.itinerary.map((day) => (
                    <motion.div
                      key={day.day}
                      initial={{ opacity: 0, y: 24 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="rounded-lg border border-white/10 bg-black/20 p-5"
                    >
                      <div className="grid items-start gap-4 md:grid-cols-[auto_minmax(0,1fr)_auto]">
                        <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-white/10 font-display text-xl font-bold">
                          {day.day}
                        </div>
                        <div>
                          <p className="font-display text-2xl font-bold tracking-[-0.05em]">{day.theme}</p>
                          <p className="mt-2 text-sm leading-7 text-white/60">{day.summary}</p>
                        </div>
                        <span className="inline-flex min-w-[132px] self-start items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm font-semibold text-white">
                          {formatCurrency(day.daily_estimate, activePlan.currency_code)}
                        </span>
                      </div>
                      <div className="mt-5 grid items-start gap-3 md:grid-cols-3">
                        {day.activities.map((activity) => (
                          <div key={activity.title} className="rounded-lg border border-white/8 bg-white/[0.04] p-4">
                            <p className="text-xs uppercase tracking-[0.24em] text-white/45">{activity.time}</p>
                            <p className="mt-2 font-semibold text-white">{activity.title}</p>
                            <p className="mt-2 text-sm text-white/58">{activity.location}</p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="soft-panel flex min-h-[460px] items-center justify-center p-10">
              <div className="max-w-xl text-center">
                <p className="eyebrow">Plan Surface</p>
                <h2 className="mt-4 font-display text-3xl font-bold tracking-[-0.055em] text-white sm:text-[3rem]">
                  Your itinerary will appear here.
                </h2>
                <p className="mt-4 text-sm leading-8 text-white/56">
                  Generate a trip to reveal live insights, cost signals, featured attractions, and a complete day-by-day route.
                </p>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default TripGeneratorPage;
