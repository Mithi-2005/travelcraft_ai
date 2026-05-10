from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx

from app.config import settings
from app.models import (
    Activity,
    Attraction,
    CustomizationSummary,
    CostBreakdown,
    DayPlan,
    HotelRecommendation,
    LocalPlace,
    LogisticsPlan,
    ResearchSource,
    SmartSuggestion,
    TripPlanLLMOutput,
    UserMemory,
)


logger = logging.getLogger(__name__)

PLACEHOLDER_OVERVIEW_PHRASES = (
    "a refined trip through ",
    " is framed as a cinematic ",
    "local flavor, and a realistic ",
)

MOOD_SIGNAL_KEYWORDS = {
    "relaxed": {
        "relaxed",
        "slow",
        "calm",
        "leisure",
        "restorative",
        "unhurried",
        "easygoing",
        "gentle",
    },
    "adventure": {
        "adventure",
        "active",
        "bold",
        "high-energy",
        "thrill",
        "trail",
        "explore",
    },
    "luxury": {
        "luxury",
        "elevated",
        "private",
        "premium",
        "signature",
        "boutique",
        "exclusive",
    },
}
BUDGET_TOLERANCE_FLOOR = 1.0
BUDGET_TOLERANCE_RATE = 0.03
MOOD_STRUCTURAL_SIGNALS = {
    "relaxed": {
        "summary": {
            "slow",
            "calm",
            "restorative",
            "gentle",
            "unhurried",
            "easygoing",
            "relaxed",
        },
        "theme": {
            "arrival",
            "orientation",
            "pause",
            "reflection",
            "slow",
            "relaxed",
            "leisure",
        },
        "activity": {
            "walk",
            "wander",
            "cafe",
            "sunset",
            "spa",
            "browse",
            "market",
            "pause",
        },
    },
    "adventure": {
        "summary": {
            "bold",
            "adventure",
            "explore",
            "active",
            "high-energy",
            "thrill",
            "movement",
        },
        "theme": {
            "signature",
            "exploration",
            "adventure",
            "outdoors",
            "active",
            "bold",
        },
        "activity": {
            "hike",
            "trail",
            "climb",
            "kayak",
            "bike",
            "explore",
            "adventure",
            "surf",
        },
    },
    "luxury": {
        "summary": {
            "luxury",
            "elevated",
            "premium",
            "exclusive",
            "private",
            "boutique",
            "signature",
        },
        "theme": {"signature", "elevated", "curated", "luxury", "private", "premium"},
        "activity": {
            "chef",
            "tasting",
            "private",
            "boutique",
            "suite",
            "spa",
            "salon",
            "concierge",
        },
    },
}


class LLMService:
    def __init__(self) -> None:
        self.providers: list[dict[str, Any]] = self._build_providers()
        self.groq_api_key = settings.groq_api_key
        self.groq_base_url = settings.groq_base_url.rstrip("/")
        self.gemini_api_key = settings.gemini_api_key
        self.gemini_base_url = settings.gemini_base_url.rstrip("/")
        self.xai_api_key = settings.xai_api_key
        self.xai_base_url = settings.xai_base_url.rstrip("/")
        self.retry_attempts = 3
        self.retry_backoff_seconds = 1.5

    def _build_providers(self) -> list[dict[str, Any]]:
        configured = {
            "gemini": {
                "label": "Gemini",
                "kind": "gemini",
                "model": settings.gemini_model,
                "enabled": bool(settings.gemini_api_key),
            },
            "groq": {
                "label": "Groq",
                "kind": "groq",
                "model": settings.groq_model,
                "enabled": bool(settings.groq_api_key),
            },
            "xai": {
                "label": "Grok/xAI",
                "kind": "xai",
                "model": settings.xai_model,
                "enabled": bool(settings.xai_api_key),
            },
        }
        providers: list[dict[str, Any]] = []
        for raw_name in settings.llm_provider_order.split(","):
            name = raw_name.strip().lower()
            provider = configured.get(name)
            if provider and provider["enabled"]:
                providers.append(
                    {key: value for key, value in provider.items() if key != "enabled"}
                )

        seen = {provider["kind"] for provider in providers}
        for name, provider in configured.items():
            if name not in seen and provider["enabled"]:
                providers.append(
                    {key: value for key, value in provider.items() if key != "enabled"}
                )
        return providers

    async def generate_trip(
        self,
        destination: str,
        days: int,
        arrival_time: str,
        traveler_count: int,
        budget: float,
        currency_code: str,
        interests: list[str],
        mood: str,
        memory: UserMemory,
        research: dict[str, Any],
        pace: str = "balanced",
        accommodation_style: str = "mixed",
        food_preference: str = "local favorites",
        must_include: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> TripPlanLLMOutput:
        if not self.providers:
            reason = "No live LLM provider configured. Check GEMINI_API_KEY, GROQ_API_KEY, or XAI_API_KEY."
            logger.warning(reason)
            return self._fallback(
                destination,
                days,
                traveler_count,
                budget,
                currency_code,
                interests,
                mood,
                research,
                reason,
                arrival_time,
            )

        try:
            attempts = 2
            retry_feedback: list[str] = []
            last_issues: list[str] = []

            for attempt in range(attempts):
                result = await asyncio.to_thread(
                    self._generate_structured_trip_with_failover,
                    destination,
                    days,
                    arrival_time,
                    traveler_count,
                    budget,
                    currency_code,
                    interests,
                    mood,
                    memory,
                    research,
                    retry_feedback,
                    pace,
                    accommodation_style,
                    food_preference,
                    must_include or [],
                    avoid or [],
                )
                result = self._enforce_user_constraints(
                    result,
                    destination=destination,
                    mood=mood,
                    research=research,
                    traveler_count=traveler_count,
                    interests=interests,
                    days=days,
                    budget=budget,
                    arrival_time=arrival_time,
                )
                issues = self._validate_generated_trip(
                    result,
                    destination,
                    days,
                    traveler_count,
                    budget,
                    currency_code,
                    interests,
                    mood,
                )
                if not issues:
                    return self._attach_service_metadata(
                        result,
                        research=research,
                        llm_mode="live",
                        llm_error=None,
                    )

                last_issues = issues
                retry_feedback = [
                    "The previous draft did not satisfy these constraints:",
                    *[f"- {issue}" for issue in issues],
                    "Regenerate the full plan and explicitly fix every issue above.",
                ]
                logger.warning(
                    "LLM itinerary validation failed for %s on attempt %s: %s",
                    destination,
                    attempt + 1,
                    "; ".join(issues),
                )

            return self._fallback(
                destination,
                days,
                traveler_count,
                budget,
                currency_code,
                interests,
                mood,
                research,
                "Generated plan failed validation: " + "; ".join(last_issues),
                arrival_time,
            )
        except Exception as exc:
            logger.exception("LLM itinerary generation failed for %s", destination)
            return self._fallback(
                destination,
                days,
                traveler_count,
                budget,
                currency_code,
                interests,
                mood,
                research,
                self._public_provider_error(exc),
                arrival_time,
            )

    def _generate_structured_trip(
        self,
        destination: str,
        days: int,
        arrival_time: str,
        traveler_count: int,
        budget: float,
        currency_code: str,
        interests: list[str],
        mood: str,
        memory: UserMemory,
        research: dict[str, Any],
        retry_feedback: list[str] | None = None,
        pace: str = "balanced",
        accommodation_style: str = "mixed",
        food_preference: str = "local favorites",
        must_include: list[str] | None = None,
        avoid: list[str] | None = None,
        *,
        provider_kind: str,
        client: Any,
        model_name: str,
    ) -> TripPlanLLMOutput:
        system_prompt = (
            "You are TravelCraft AI, a practical travel planner. Produce a clear, realistic, "
            "budget-aware itinerary using the supplied research and memory. Use simple English, short sentences, "
            "and useful local details. Treat the user's chosen destination, budget, interests, and mood as strict requirements."
        )
        retry_notes = "\n".join(retry_feedback or [])
        traveler_label = self._traveler_phrase(traveler_count)
        user_prompt = f"""
Create a {days}-day personalized trip plan.

Requested destination: {destination}
Trip length: {days} days
Arrival time at destination: {arrival_time}
Travel party: {traveler_label}
Budget: {budget} {currency_code} total for the entire group
Required mood: {mood}
Required interests: {", ".join(interests) or "general discovery"}
Plan pace: {pace}
Accommodation style: {accommodation_style}
Food preference: {food_preference}
Must include: {", ".join(must_include or []) or "none"}
Avoid: {", ".join(avoid or []) or "none"}

Traveler memory:
- Name: {memory.name}
- Travel style: {memory.travel_style}
- Preferred mood: {memory.preferred_mood}
- Stored interests: {", ".join(memory.interests)}
- Past trip count: {len(memory.past_trips)}

Live destination research:
{chr(10).join(f"- {item}" for item in research.get("summary", []))}

Strict output requirements:
- Keep costs plausible and make cost_breakdown.total equal the requested budget in {currency_code}.
- Treat the budget as the full-trip ceiling in INR for {traveler_label}, not as a per-day or per-person amount.
- The destination must stay exactly {destination}.
- The itinerary must include exactly {days} days, numbered 1 through {days}.
- Day 1 must start after the arrival time, leaving realistic buffer for transfer, check-in, food, and rest.
- Use simple English. Write short, clear sentences that normal users can understand quickly.
- Keep the plan clean. Avoid unnecessary background, marketing language, and generic filler.
- Activity titles must sound like real trip stops or experiences, not placeholders like "Day 2 stop 4" or "planned activity".
- Each activity description should be short, concrete, and place-aware. Keep it to one or two small sentences.
- Each recommendation must make sense for {traveler_label}; adapt table sizes, room logic, logistics, and pacing to the party size.
- Make the requested mood obvious in the overview, daily pacing, and activity choices.
- Use the exact interest words where relevant so the match is visible in attractions, itinerary items, or suggestions.
- All monetary values must be practical for {destination} and expressed in {currency_code}.
- If local pricing is typically published in another currency, convert it into realistic traveler-facing estimates in {currency_code}.
- Include 3 featured attractions.
- Include 4 hotel_recommendations with real-sounding area guidance, category, nightly estimate, fit reason, and booking tip.
- Include 6 local_places across restaurants, neighborhoods, markets, viewpoints, museums, and hidden gems when relevant.
- The itinerary activities must actively reuse the named hotel base, featured attractions, and local_places where they fit. Do not keep those sections separate from the day plan.
- Mention those chosen place names directly inside itinerary activity titles or locations when they are being used.
- Include logistics with arrival transfer, local transport, neighborhood base, booking priorities, safety notes, and packing notes.
- Include customization summarizing pace, accommodation_style, food_preference, must_include, and avoid.
- Each day should have at least 3 activities and mandatory Breakfast, Lunch, and Dinner plans.
- Add a Snacks stop when the day is fuller or has longer gaps between activities.
- Do not force the same number of activities every day. Use 3 to 5 activities based on arrival time, transfer load, pacing, distance between stops, and the trip mood.
- Arrival and departure days can be lighter. Full exploration days should usually contain more stops when realistic.
- Daily estimates should vary based on the actual plan. Do not split the budget equally across all days.
- Higher-cost days should show why they cost more, such as hotels, transfers, guided visits, or premium meals.
- Smart suggestions should connect to the user's memory and past behavior.
- Avoid generic filler; keep the itinerary elegant, specific, and useful.
- If the mood is relaxed, bias toward slower pacing, restorative windows, and fewer hard transitions.
- If the mood is adventure, bias toward energetic movement, exploration, and bolder experiences.
- If the mood is luxury, bias toward elevated stays, signature dining, boutique service, and premium touches.

Validation target:
- At least one chosen interest must appear clearly in attractions, activities, or suggestions.
- The response should be easy to audit for destination, budget, interests, and mood alignment.

{retry_notes}
"""

        if provider_kind == "groq":
            return self._generate_with_openai_compatible(
                provider_name="Groq",
                base_url=self.groq_base_url,
                api_key=self.groq_api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                destination=destination,
                days=days,
                budget=budget,
            )
        if provider_kind == "xai":
            return self._generate_with_openai_compatible(
                provider_name="Grok/xAI",
                base_url=self.xai_base_url,
                api_key=self.xai_api_key,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                destination=destination,
                days=days,
                budget=budget,
            )
        if provider_kind == "gemini":
            return self._generate_with_gemini(
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                destination=destination,
                days=days,
                budget=budget,
            )

        raise RuntimeError(f"Unsupported provider kind: {provider_kind}")

    def _generate_structured_trip_with_failover(
        self,
        destination: str,
        days: int,
        arrival_time: str,
        traveler_count: int,
        budget: float,
        currency_code: str,
        interests: list[str],
        mood: str,
        memory: UserMemory,
        research: dict[str, Any],
        retry_feedback: list[str] | None = None,
        pace: str = "balanced",
        accommodation_style: str = "mixed",
        food_preference: str = "local favorites",
        must_include: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> TripPlanLLMOutput:
        last_error: Exception | None = None
        for provider_index, provider in enumerate(self.providers):
            provider_label = str(provider["label"])
            provider_kind = str(provider["kind"])
            client = provider.get("client")
            model_name = str(provider["model"])
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    return self._generate_structured_trip(
                        destination,
                        days,
                        arrival_time,
                        traveler_count,
                        budget,
                        currency_code,
                        interests,
                        mood,
                        memory,
                        research,
                        retry_feedback,
                        pace,
                        accommodation_style,
                        food_preference,
                        must_include or [],
                        avoid or [],
                        provider_kind=provider_kind,
                        client=client,
                        model_name=model_name,
                    )
                except Exception as exc:
                    last_error = exc
                    if self._is_provider_quota_error(exc):
                        logger.warning(
                            "%s quota/rate limit reached for %s using model %s; trying next provider if available.",
                            provider_label,
                            destination,
                            model_name,
                        )
                        break

                    if not self._is_transient_provider_error(exc):
                        raise

                    logger.warning(
                        "Transient %s error for %s using %s with model %s (attempt %s/%s): %s",
                        provider_kind.upper(),
                        destination,
                        provider_label,
                        model_name,
                        attempt,
                        self.retry_attempts,
                        exc,
                    )
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_backoff_seconds * attempt)

            if provider_index < len(self.providers) - 1:
                logger.warning(
                    "Switching live LLM generation from %s to %s after repeated transient errors.",
                    provider_label,
                    self.providers[provider_index + 1]["label"],
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("Live generation failed without a captured provider error.")

    def _validate_generated_trip(
        self,
        result: TripPlanLLMOutput,
        destination: str,
        days: int,
        traveler_count: int,
        budget: float,
        currency_code: str,
        interests: list[str],
        mood: str,
    ) -> list[str]:
        issues: list[str] = []

        total = float(result.cost_breakdown.total)
        tolerance = max(BUDGET_TOLERANCE_FLOOR, budget * BUDGET_TOLERANCE_RATE)
        if abs(total - budget) > tolerance:
            issues.append(
                f"Budget total {total:.2f} {currency_code} does not align with requested budget {budget:.2f} {currency_code} within tolerance {tolerance:.2f}."
            )

        search_haystack = " ".join(
            [
                result.overview,
                result.best_time_to_visit,
                *result.live_insights,
                *[
                    " ".join(
                        [
                            attraction.name,
                            attraction.reason,
                            attraction.best_time,
                        ]
                    )
                    for attraction in result.attractions
                ],
                *[
                    " ".join(
                        [
                            day.theme,
                            day.summary,
                            " ".join(
                                " ".join(
                                    [
                                        activity.title,
                                        activity.location,
                                        activity.description,
                                    ]
                                )
                                for activity in day.activities
                            ),
                            " ".join(day.meals),
                        ]
                    )
                    for day in result.itinerary
                ],
                *[
                    " ".join([suggestion.title, suggestion.description])
                    for suggestion in result.smart_suggestions
                ],
            ]
        ).lower()

        destination_markers = self._destination_markers(destination)
        if not self._matches_destination(search_haystack, destination_markers):
            issues.append(
                f"Destination {destination} is not reflected clearly in the generated content."
            )

        traveler_markers = {
            str(traveler_count),
            self._traveler_phrase(traveler_count).lower(),
            ("solo" if traveler_count == 1 else ""),
            ("couple" if traveler_count == 2 else ""),
            ("group" if traveler_count >= 3 else ""),
        }
        traveler_markers.discard("")
        if not any(marker in search_haystack for marker in traveler_markers):
            issues.append(
                f"Traveler count of {traveler_count} is not reflected clearly in the generated content or planning language."
            )

        matched_interest = False
        for interest in interests:
            if interest.lower() in search_haystack:
                matched_interest = True
                break
        if interests and not matched_interest:
            issues.append(
                "Selected interests are not reflected clearly in attractions, itinerary items, or suggestions."
            )

        mood_keywords = MOOD_SIGNAL_KEYWORDS.get(mood, {mood})
        if not any(keyword in search_haystack for keyword in mood_keywords):
            issues.append(
                f"Requested mood {mood} is not obvious in the generated pacing and tone."
            )
        else:
            structure_issues = self._validate_mood_structure(result, mood)
            issues.extend(structure_issues)

        if len(result.itinerary) != days:
            issues.append(f"The itinerary must include exactly {days} days.")

        if any(len(day.activities) < 3 for day in result.itinerary):
            issues.append("Each itinerary day must include at least 3 activities.")

        if any(not self._has_required_meals(day.meals) for day in result.itinerary):
            issues.append("Each itinerary day must include Breakfast, Lunch, and Dinner.")

        if len(result.attractions) != 3:
            issues.append("The plan must include exactly 3 featured attractions.")

        return issues

    def _enforce_user_constraints(
        self,
        result: TripPlanLLMOutput,
        *,
        destination: str,
        mood: str,
        research: dict[str, Any],
        traveler_count: int | None = None,
        interests: list[str] | None = None,
        days: int | None = None,
        budget: float | None = None,
        arrival_time: str = "10:00",
    ) -> TripPlanLLMOutput:
        normalized_destination = destination.strip()
        if days:
            result.itinerary = self._repair_itinerary_length(
                result.itinerary,
                target_days=days,
                destination=normalized_destination or destination,
                mood=mood,
                traveler_count=traveler_count,
                interests=interests or [],
                budget=budget,
                arrival_time=arrival_time,
            )
        self._integrate_plan_places_into_itinerary(
            result,
            destination=normalized_destination or destination,
            mood=mood,
        )

        mood_label = mood.capitalize()
        mood_signals = MOOD_STRUCTURAL_SIGNALS.get(mood, {})
        theme_terms = mood_signals.get("theme", {mood.lower()})
        for day in result.itinerary:
            if not any(term in day.theme.lower() for term in theme_terms):
                day.theme = f"{mood_label} {day.theme}".strip()
            day.activities = self._repair_day_activities(
                day.activities,
                day.day,
                normalized_destination,
                mood,
                total_days=len(result.itinerary),
            )
            day.meals = self._repair_day_meals(
                day.meals,
                day.day,
                normalized_destination,
                activity_count=len(day.activities),
            )
        self._repair_daily_estimates(result)

        if self._overview_needs_rewrite(result.overview):
            result.overview = self._build_itinerary_overview(
                destination=normalized_destination or destination,
                itinerary=result.itinerary,
                mood=mood,
                traveler_count=traveler_count,
                interests=interests or [],
                days=days,
            )
        elif (
            normalized_destination
            and normalized_destination.lower() not in result.overview.lower()
        ):
            result.overview = f"{result.overview.rstrip()} This trip is specifically planned for {normalized_destination}."

        best_time_hint = str(research.get("best_time_hint", "")).strip()
        if best_time_hint:
            result.best_time_to_visit = best_time_hint

        return result

    def _integrate_plan_places_into_itinerary(
        self,
        result: TripPlanLLMOutput,
        *,
        destination: str,
        mood: str,
    ) -> None:
        if not result.itinerary:
            return

        assets = self._build_itinerary_assets(result, destination=destination)
        if not assets:
            return

        total_days = len(result.itinerary)
        day_cursor = 0
        for asset in assets:
            if self._itinerary_already_mentions_asset(result.itinerary, asset["name"]):
                continue

            placed = False
            for offset in range(total_days):
                day_index = (day_cursor + offset) % total_days
                day = result.itinerary[day_index]
                day_limit = max(
                    self._target_activity_count(
                        day_number=day.day,
                        total_days=total_days,
                        mood=mood,
                    ),
                    5,
                )
                if len(day.activities) < day_limit:
                    day.activities.append(
                        Activity(
                            title=asset["title"],
                            time=self._next_activity_time(day.activities),
                            location=asset["location"],
                            description=asset["description"],
                            estimated_cost=asset["estimated_cost"],
                        )
                    )
                    placed = True
                    day_cursor = (day_index + 1) % total_days
                    break

                replace_index = self._find_replaceable_activity_index(day.activities)
                if replace_index is not None:
                    existing = day.activities[replace_index]
                    day.activities[replace_index] = Activity(
                        title=asset["title"],
                        time=existing.time,
                        location=asset["location"],
                        description=asset["description"],
                        estimated_cost=max(asset["estimated_cost"], existing.estimated_cost),
                    )
                    placed = True
                    day_cursor = (day_index + 1) % total_days
                    break

            if not placed:
                target_day = result.itinerary[day_cursor % total_days]
                target_day.activities.append(
                    Activity(
                        title=asset["title"],
                        time=self._next_activity_time(target_day.activities),
                        location=asset["location"],
                        description=asset["description"],
                        estimated_cost=asset["estimated_cost"],
                    )
                )
                day_cursor = (day_cursor + 1) % total_days

    def _build_itinerary_assets(
        self, result: TripPlanLLMOutput, *, destination: str
    ) -> list[dict[str, Any]]:
        assets: list[dict[str, Any]] = []

        if result.hotel_recommendations:
            primary_hotel = result.hotel_recommendations[0]
            assets.append(
                {
                    "name": primary_hotel.name,
                    "title": f"Check in at {primary_hotel.name}",
                    "location": primary_hotel.area or destination,
                    "description": self._shorten_copy(
                        primary_hotel.why_it_fits
                        or f"Use this as the main base for smoother movement across {destination}.",
                        max_words=18,
                    ),
                    "estimated_cost": 0.0,
                }
            )

        for attraction in result.attractions:
            assets.append(
                {
                    "name": attraction.name,
                    "title": attraction.name,
                    "location": destination,
                    "description": self._shorten_copy(
                        f"{attraction.reason} Best around {attraction.best_time}.",
                        max_words=18,
                    ),
                    "estimated_cost": attraction.estimated_cost,
                }
            )

        for place in result.local_places:
            assets.append(
                {
                    "name": place.name,
                    "title": place.name,
                    "location": place.area or destination,
                    "description": self._shorten_copy(
                        f"{place.why_go} Best for {place.best_time.lower()} visits.",
                        max_words=18,
                    ),
                    "estimated_cost": place.estimated_cost,
                }
            )

        return assets

    def _itinerary_already_mentions_asset(
        self, itinerary: list[DayPlan], asset_name: str
    ) -> bool:
        needle = asset_name.strip().lower()
        if not needle:
            return False
        return any(
            needle in " ".join(
                [activity.title, activity.location, activity.description]
            ).lower()
            for day in itinerary
            for activity in day.activities
        )

    def _find_replaceable_activity_index(
        self, activities: list[Activity]
    ) -> int | None:
        scored: list[tuple[int, int]] = []
        for index, activity in enumerate(activities):
            title = activity.title.strip().lower()
            location = activity.location.strip().lower()
            description = activity.description.strip().lower()
            score = 0
            if title and title not in {"planned activity"} and not re.fullmatch(
                r"day \d+ (activity|stop) \d+", title
            ):
                score += 1
            if location not in {
                "",
                "destination",
                "the destination",
                "destination center",
                "destination district",
                "destination viewpoint",
            }:
                score += 1
            if description and description not in {
                "a relevant stop for the trip.",
                "a relevant stop for the trip",
            }:
                score += 1
            scored.append((score, index))

        scored.sort(key=lambda item: item[0])
        if scored and scored[0][0] <= 1:
            return scored[0][1]
        return None

    def _next_activity_time(self, activities: list[Activity]) -> str:
        preset = ["09:00", "11:00", "13:00", "16:00", "18:30", "20:30"]
        if len(activities) < len(preset):
            return preset[len(activities)]
        return preset[-1]

    def _shorten_copy(self, text: str, *, max_words: int) -> str:
        words = text.strip().split()
        if len(words) <= max_words:
            return text.strip()
        return " ".join(words[:max_words]).rstrip(".,") + "."

    def _repair_itinerary_length(
        self,
        itinerary: list[DayPlan],
        *,
        target_days: int,
        destination: str,
        mood: str,
        traveler_count: int | None,
        interests: list[str],
        budget: float | None,
        arrival_time: str,
    ) -> list[DayPlan]:
        repaired_days = [day.model_copy(deep=True) for day in itinerary[:target_days]]
        traveler_label = self._traveler_phrase(traveler_count or 1)
        interest_a = interests[0] if interests else "culture"
        interest_b = interests[1] if len(interests) > 1 else "food"
        budget_total = float(budget or 0)
        daily_base = (
            round(budget_total / max(target_days, 1), 2) if budget_total > 0 else 0.0
        )
        activity_cost = round(daily_base * 0.28, 2) if daily_base > 0 else 0.0
        fallback_days = self._build_fallback_itinerary(
            destination=destination,
            days=target_days,
            traveler_label=traveler_label,
            mood=mood,
            interest_a=interest_a,
            interest_b=interest_b,
            daily_base=daily_base,
            activity_cost=activity_cost,
            arrival_time=arrival_time,
        )

        normalized: list[DayPlan] = []
        for index in range(target_days):
            fallback_day = fallback_days[index]
            if index < len(repaired_days):
                current = repaired_days[index]
                current.day = index + 1
                if not current.theme.strip():
                    current.theme = fallback_day.theme
                if not current.summary.strip():
                    current.summary = fallback_day.summary
                if self._activities_need_fallback(current.activities):
                    current.activities = [
                        activity.model_copy(deep=True)
                        for activity in fallback_day.activities
                    ]
                if len([meal for meal in current.meals if meal.strip()]) < 2:
                    current.meals = list(fallback_day.meals)
                normalized.append(current)
            else:
                normalized.append(fallback_day.model_copy(deep=True))
        return normalized

    def _activities_need_fallback(self, activities: list[Activity]) -> bool:
        if not activities:
            return True

        placeholder_titles = {
            "planned activity",
            "relaxed activity",
            "adventure activity",
            "luxury activity",
        }
        generic_locations = {"destination", "the destination", "destination center"}
        meaningful = 0
        for activity in activities:
            title = activity.title.strip().lower()
            location = activity.location.strip().lower()
            description = activity.description.strip().lower()
            if (
                title
                and title not in placeholder_titles
                and "day " not in title
                and "circuit" not in title
                and location not in generic_locations
                and description
                not in {
                    "a relevant stop for the trip.",
                    "a relevant stop for the trip".lower(),
                }
            ):
                meaningful += 1
        return meaningful == 0

    def _overview_needs_rewrite(self, overview: str) -> bool:
        cleaned = overview.strip().lower()
        if not cleaned:
            return True
        if cleaned in {"overview", "trip overview", "summary"}:
            return True
        if len(cleaned.split()) < 6:
            return True
        return any(marker in cleaned for marker in PLACEHOLDER_OVERVIEW_PHRASES)

    def _build_itinerary_overview(
        self,
        *,
        destination: str,
        itinerary: list[DayPlan],
        mood: str,
        traveler_count: int | None,
        interests: list[str],
        days: int | None,
    ) -> str:
        destination_label = destination or "this destination"
        day_count = days or len(itinerary)
        traveler_text = (
            f" for {self._traveler_phrase(traveler_count)}"
            if traveler_count
            else ""
        )
        cleaned_interests = [item.strip() for item in interests if item and item.strip()]
        interest_text = ""
        if cleaned_interests:
            if len(cleaned_interests) == 1:
                interest_text = f", with a clear focus on {cleaned_interests[0]}"
            else:
                interest_text = (
                    f", balancing {cleaned_interests[0]} and {cleaned_interests[1]}"
                )

        if not itinerary:
            return (
                f"This {day_count}-day {mood} trip to {destination_label}{traveler_text}"
                f"{interest_text} is being prepared with a practical day-by-day structure."
            )

        first_day = itinerary[0]
        last_day = itinerary[-1]
        highlight_titles = [
            activity.title.strip()
            for day in itinerary[: min(3, len(itinerary))]
            for activity in day.activities[:1]
            if activity.title.strip()
        ]
        highlight_text = ""
        if highlight_titles:
            if len(highlight_titles) == 1:
                highlight_text = f" Highlights include {highlight_titles[0]}."
            elif len(highlight_titles) == 2:
                highlight_text = (
                    f" Highlights include {highlight_titles[0]} and {highlight_titles[1]}."
                )
            else:
                highlight_text = (
                    f" Highlights include {highlight_titles[0]}, {highlight_titles[1]},"
                    f" and {highlight_titles[2]}."
                )

        return (
            f"This {day_count}-day {mood} trip to {destination_label}{traveler_text}{interest_text} "
            f"starts with Day 1 focused on {first_day.theme.lower()} and wraps with Day {last_day.day} centered on "
            f"{last_day.theme.lower()}.{highlight_text}"
        )

    def _repair_day_activities(
        self,
        activities: list[Activity],
        day_number: int,
        destination: str,
        mood: str,
        *,
        total_days: int | None = None,
    ) -> list[Activity]:
        repaired = [
            activity.model_copy(deep=True)
            for activity in activities
            if activity.title.strip()
        ]

        mood_signals = MOOD_STRUCTURAL_SIGNALS.get(mood, {})
        activity_terms = mood_signals.get("activity", {mood.lower()})
        destination_label = destination or "the destination"
        emphasis = sorted(activity_terms)[0]
        target_count = self._target_activity_count(
            day_number=day_number,
            total_days=total_days or day_number,
            mood=mood,
        )
        has_mood_signal = any(
            any(
                term
                in " ".join(
                    [activity.title, activity.location, activity.description]
                ).lower()
                for term in activity_terms
            )
            for activity in repaired
        )

        if repaired and not has_mood_signal:
            repaired[0].title = self._mood_activity_title(
                repaired[0].title, emphasis, mood
            )
            repaired[0].description = self._mood_activity_description(
                repaired[0].description, mood, destination_label
            )
        repaired = [
            self._refine_activity_copy(
                activity,
                day_number=day_number,
                activity_number=index + 1,
                destination=destination_label,
                mood=mood,
                emphasis=emphasis,
            )
            for index, activity in enumerate(repaired)
        ]

        if repaired:
            while len(repaired) < target_count:
                next_index = len(repaired) + 1
                repaired.append(
                    self._build_extra_activity(
                        day_number=day_number,
                        activity_number=next_index,
                        destination=destination_label,
                        mood=mood,
                        emphasis=emphasis,
                        estimated_cost=(
                            repaired[-1].estimated_cost
                            if repaired[-1].estimated_cost
                            else 0
                        ),
                    )
                )
            return repaired

        rebuilt = [
            Activity(
                title=self._mood_activity_title(
                    f"Arrival circuit {day_number}", emphasis, mood
                ),
                time="09:00",
                location=f"{destination_label} center",
                description=self._mood_activity_description(
                    f"Start with a {mood} route that gives a clear first taste of {destination_label}.",
                    mood,
                    destination_label,
                ),
                estimated_cost=0,
            ),
            Activity(
                title=self._mood_activity_title(
                    f"Midday circuit {day_number}", emphasis, mood
                ),
                time="13:00",
                location=f"{destination_label} district",
                description=self._mood_activity_description(
                    f"Keep the pace active and specific to the trip mood in {destination_label}.",
                    mood,
                    destination_label,
                ),
                estimated_cost=0,
            ),
            Activity(
                title=self._mood_activity_title(
                    f"Evening circuit {day_number}", emphasis, mood
                ),
                time="18:00",
                location=f"{destination_label} viewpoint",
                description=self._mood_activity_description(
                    f"Close with a mood-aligned finish that feels easy to audit and clearly tied to {destination_label}.",
                    mood,
                    destination_label,
                ),
                estimated_cost=0,
            ),
        ]
        while len(rebuilt) < target_count:
            next_index = len(rebuilt) + 1
            rebuilt.append(
                self._build_extra_activity(
                    day_number=day_number,
                    activity_number=next_index,
                    destination=destination_label,
                    mood=mood,
                    emphasis=emphasis,
                    estimated_cost=0,
                )
            )
        return rebuilt

    def _refine_activity_copy(
        self,
        activity: Activity,
        *,
        day_number: int,
        activity_number: int,
        destination: str,
        mood: str,
        emphasis: str,
    ) -> Activity:
        refined = activity.model_copy(deep=True)
        title = refined.title.strip()
        location = refined.location.strip()
        description = refined.description.strip()

        if self._activity_title_needs_upgrade(title):
            replacement = self._build_extra_activity(
                day_number=day_number,
                activity_number=max(activity_number, 4),
                destination=destination,
                mood=mood,
                emphasis=emphasis,
                estimated_cost=refined.estimated_cost,
            )
            refined.title = replacement.title
            if self._location_needs_upgrade(location):
                refined.location = replacement.location
            if self._description_needs_upgrade(description):
                refined.description = replacement.description
            return refined

        if self._location_needs_upgrade(location):
            refined.location = self._upgrade_location_from_title(title, destination)
        if self._description_needs_upgrade(description):
            refined.description = self._build_short_place_description(
                title=refined.title,
                location=refined.location,
                mood=mood,
                destination=destination,
            )
        return refined

    def _activity_title_needs_upgrade(self, title: str) -> bool:
        cleaned = title.strip().lower()
        if not cleaned:
            return True
        if cleaned == "planned activity":
            return True
        return bool(re.fullmatch(r"day \d+ (activity|stop) \d+", cleaned))

    def _location_needs_upgrade(self, location: str) -> bool:
        cleaned = location.strip().lower()
        return cleaned in {
            "",
            "destination",
            "the destination",
            "destination center",
            "destination district",
            "destination viewpoint",
        }

    def _description_needs_upgrade(self, description: str) -> bool:
        cleaned = description.strip().lower()
        if not cleaned:
            return True
        return cleaned in {
            "a relevant stop for the trip.",
            "a relevant stop for the trip",
        } or cleaned.startswith("a relaxed stop that keeps the day moving") or cleaned.startswith(
            "a adventure stop that keeps the day moving"
        ) or cleaned.startswith("a luxury stop that keeps the day moving")

    def _upgrade_location_from_title(self, title: str, destination: str) -> str:
        lowered = title.lower()
        if any(token in lowered for token in {"cafe", "coffee", "brunch", "breakfast"}):
            return f"{destination} cafe quarter"
        if any(token in lowered for token in {"market", "bazaar", "shopping"}):
            return f"{destination} market lane"
        if any(token in lowered for token in {"sunset", "walk", "promenade", "view", "terrace"}):
            return f"{destination} scenic waterfront"
        if any(token in lowered for token in {"museum", "gallery", "design"}):
            return f"{destination} cultural district"
        if any(token in lowered for token in {"dinner", "lunch", "food", "tasting", "restaurant"}):
            return f"{destination} dining quarter"
        return f"{destination} central district"

    def _build_short_place_description(
        self,
        *,
        title: str,
        location: str,
        mood: str,
        destination: str,
    ) -> str:
        lowered = title.lower()
        if any(token in lowered for token in {"cafe", "coffee", "breakfast", "brunch"}):
            base = f"A short food-led pause around {location} with an easy local rhythm."
        elif any(token in lowered for token in {"market", "bazaar", "shopping"}):
            base = f"A compact browse through {location} for local texture, snacks, and small finds."
        elif any(token in lowered for token in {"museum", "gallery", "design"}):
            base = f"A light cultural stop in {location} with enough time to look around without rushing."
        elif any(token in lowered for token in {"walk", "sunset", "terrace", "view", "promenade"}):
            base = f"A scenic stop around {location} that fits the best light and a calmer pace."
        elif any(token in lowered for token in {"dinner", "lunch", "tasting", "restaurant"}):
            base = f"A focused meal stop in {location} that adds a clear taste of {destination}."
        else:
            base = f"A short stop around {location} that fits naturally into the day."
        return self._mood_activity_description(base, mood, destination)

    def _target_activity_count(
        self,
        *,
        day_number: int,
        total_days: int,
        mood: str,
    ) -> int:
        if day_number == 1:
            return 3
        if day_number == total_days:
            return 3 if mood == "relaxed" else 4
        if mood == "adventure":
            return 5 if total_days >= 4 else 4
        if mood == "luxury":
            return 4
        return 4

    def _build_extra_activity(
        self,
        *,
        day_number: int,
        activity_number: int,
        destination: str,
        mood: str,
        emphasis: str,
        estimated_cost: float,
    ) -> Activity:
        extra_slots = [
            (
                "11:00",
                "Cafe quarter",
                "Late-morning cafe reset",
                "A short food-led pause with time to settle into the neighborhood pace.",
            ),
            (
                "15:30",
                "Market lane",
                "Market lane browse",
                "A compact local browse that adds texture without stretching transfers.",
            ),
            (
                "17:00",
                "Scenic stop",
                "Golden-hour scenic stop",
                "A quick viewpoint window timed for softer light and a lighter transition.",
            ),
            (
                "20:30",
                "Evening social district",
                "After-dinner local stroll",
                "A final atmosphere-led stop for a small walk, music, or street energy.",
            ),
        ]
        slot_index = max(activity_number - 4, 0) % len(extra_slots)
        time, location, title, description = extra_slots[slot_index]
        return Activity(
            title=self._mood_activity_title(title, emphasis, mood),
            time=time,
            location=f"{destination} {location}",
            description=self._mood_activity_description(
                description,
                mood,
                destination,
            ),
            estimated_cost=estimated_cost,
        )

    def _mood_activity_title(self, base_title: str, emphasis: str, mood: str) -> str:
        title = base_title.strip() or f"{mood.capitalize()} activity"
        lower_title = title.lower()
        if emphasis in lower_title or mood.lower() in lower_title:
            return title
        return f"{mood.capitalize()} {emphasis} {title}".strip()

    def _mood_activity_description(
        self, base_description: str, mood: str, destination: str
    ) -> str:
        description = base_description.strip()
        if mood.lower() in description.lower():
            return description
        return f"{description} This keeps the {mood} tone clear for {destination}."

    def _repair_daily_estimates(self, result: TripPlanLLMOutput) -> None:
        if not result.itinerary:
            return

        estimates = [
            round(float(day.daily_estimate or 0), 2) for day in result.itinerary
        ]
        has_variation = len(set(estimates)) > 1
        has_positive = any(value > 0 for value in estimates)
        if has_variation and has_positive:
            return

        total_trip_budget = float(result.cost_breakdown.total or 0)
        itinerary_budget = total_trip_budget * 0.58 if total_trip_budget > 0 else 0
        if itinerary_budget <= 0:
            itinerary_budget = sum(
                sum(float(activity.estimated_cost or 0) for activity in day.activities)
                for day in result.itinerary
            )
        if itinerary_budget <= 0:
            return

        weights: list[float] = []
        for index, day in enumerate(result.itinerary):
            activity_total = sum(
                float(activity.estimated_cost or 0) for activity in day.activities
            )
            day_weight = max(activity_total, 1.0)
            if index == 0:
                day_weight *= 0.82
            elif index == len(result.itinerary) - 1:
                day_weight *= 0.9
            else:
                day_weight *= 1.08 if index % 2 else 1.0
            weights.append(day_weight)

        total_weight = sum(weights) or float(len(weights))
        remaining = round(itinerary_budget, 2)
        for index, day in enumerate(result.itinerary):
            if index == len(result.itinerary) - 1:
                day.daily_estimate = max(round(remaining, 2), 0)
            else:
                estimate = round(itinerary_budget * (weights[index] / total_weight), 2)
                day.daily_estimate = estimate
                remaining -= estimate

    def _repair_day_meals(
        self,
        meals: list[str],
        day_number: int,
        destination: str,
        *,
        activity_count: int,
    ) -> list[str]:
        destination_label = destination or "the destination"
        normalized_slots: dict[str, str] = {}
        slot_order = ["breakfast", "lunch", "dinner", "snacks"]

        for meal in meals:
            cleaned = meal.strip()
            if not cleaned:
                continue
            slot = self._classify_meal_slot(cleaned)
            if slot and slot not in normalized_slots:
                normalized_slots[slot] = self._format_meal_slot(slot, cleaned)
                continue

            for candidate in slot_order:
                if candidate not in normalized_slots:
                    normalized_slots[candidate] = self._format_meal_slot(
                        candidate, cleaned
                    )
                    break

        defaults = {
            "breakfast": f"Breakfast - Near your {destination_label} stay",
            "lunch": f"Lunch - Local stop for day {day_number} in {destination_label}",
            "dinner": f"Dinner - Relaxed reservation in {destination_label}",
            "snacks": f"Snacks - Tea, coffee, or a quick bite around {destination_label}",
        }
        for slot in ("breakfast", "lunch", "dinner"):
            if slot not in normalized_slots:
                normalized_slots[slot] = defaults[slot]

        if activity_count >= 4 and "snacks" not in normalized_slots:
            normalized_slots["snacks"] = defaults["snacks"]

        ordered_slots = ["breakfast", "lunch"]
        if "snacks" in normalized_slots:
            ordered_slots.append("snacks")
        ordered_slots.append("dinner")
        return [normalized_slots[slot] for slot in ordered_slots]

    def _classify_meal_slot(self, meal: str) -> str | None:
        lowered = meal.lower()
        if "breakfast" in lowered or "brunch" in lowered:
            return "breakfast"
        if "lunch" in lowered:
            return "lunch"
        if "dinner" in lowered or "supper" in lowered:
            return "dinner"
        if any(token in lowered for token in {"snack", "tea", "coffee", "cafe"}):
            return "snacks"
        return None

    def _format_meal_slot(self, slot: str, meal: str) -> str:
        cleaned = meal.strip()
        label_map = {
            "breakfast": "Breakfast",
            "lunch": "Lunch",
            "dinner": "Dinner",
            "snacks": "Snacks",
        }
        if "-" in cleaned:
            prefix, detail = [part.strip() for part in cleaned.split("-", 1)]
            if prefix:
                return f"{label_map[slot]} - {detail or prefix}"
        if ":" in cleaned:
            prefix, detail = [part.strip() for part in cleaned.split(":", 1)]
            if prefix:
                return f"{label_map[slot]} - {detail or prefix}"
        if cleaned.lower().startswith(label_map[slot].lower()):
            return cleaned
        return f"{label_map[slot]} - {cleaned}"

    def _has_required_meals(self, meals: list[str]) -> bool:
        seen = {self._classify_meal_slot(meal) for meal in meals if meal.strip()}
        return {"breakfast", "lunch", "dinner"}.issubset(seen)

    def _validate_mood_structure(
        self, result: TripPlanLLMOutput, mood: str
    ) -> list[str]:
        signals = MOOD_STRUCTURAL_SIGNALS.get(mood)
        if not signals:
            return []

        overview_text = result.overview.lower()
        theme_text = " ".join(day.theme.lower() for day in result.itinerary)
        activity_text = " ".join(
            " ".join([activity.title, activity.description]).lower()
            for day in result.itinerary
            for activity in day.activities
        )

        issues: list[str] = []
        if not any(term in overview_text for term in signals["summary"]):
            issues.append(
                f"Requested mood {mood} is not reflected clearly in the overview language."
            )
        if not any(term in theme_text for term in signals["theme"]):
            issues.append(
                f"Requested mood {mood} is not reflected clearly in day themes."
            )
        if not any(term in activity_text for term in signals["activity"]):
            issues.append(
                f"Requested mood {mood} is not reflected clearly in activity choices."
            )
        return issues

    def _fallback(
        self,
        destination: str,
        days: int,
        traveler_count: int,
        budget: float,
        currency_code: str,
        interests: list[str],
        mood: str,
        research: dict[str, Any],
        error: str | None = None,
        arrival_time: str = "10:00",
    ) -> TripPlanLLMOutput:
        interest_a = interests[0] if interests else "culture"
        interest_b = interests[1] if len(interests) > 1 else "food"
        traveler_label = self._traveler_phrase(traveler_count)
        daily_base = round(budget / max(days, 1), 2)
        activity_cost = round(daily_base * 0.28, 2)
        itinerary = self._build_fallback_itinerary(
            destination=destination,
            days=days,
            traveler_label=traveler_label,
            mood=mood,
            interest_a=interest_a,
            interest_b=interest_b,
            daily_base=daily_base,
            activity_cost=activity_cost,
            arrival_time=arrival_time,
        )
        cost_breakdown = CostBreakdown(
            accommodation=round(budget * 0.36, 2),
            food=round(budget * 0.2, 2),
            transport=round(budget * 0.12, 2),
            activities=round(budget * 0.24, 2),
            contingency=round(budget * 0.08, 2),
            total=round(budget, 2),
        )
        result = TripPlanLLMOutput(
            overview=self._build_itinerary_overview(
                destination=destination,
                itinerary=itinerary,
                mood=mood,
                traveler_count=traveler_count,
                interests=interests,
                days=days,
            ),
            best_time_to_visit=str(
                research.get("best_time_hint")
                or "Aim for the destination's mild or dry season for the smoothest overall trip experience"
            ),
            live_insights=research.get("summary", [])[:3],
            customization=CustomizationSummary(
                pace="balanced",
                accommodation_style="boutique hotel or polished local stay",
                food_preference=f"{interest_b}-forward local favorites",
                must_include=[interest_a],
                avoid=["overpacked transfer days"],
            ),
            hotel_recommendations=[
                HotelRecommendation(
                    name=f"{destination} central boutique stay",
                    area="Central, walkable base",
                    category="boutique hotel",
                    nightly_estimate=round((budget * 0.36) / max(days, 1), 2),
                    why_it_fits=f"Keeps {traveler_label} close to restaurants, transit, and first-time landmarks.",
                    booking_tip="Prioritize recent reviews mentioning cleanliness, location, and breakfast quality.",
                ),
                HotelRecommendation(
                    name=f"{destination} comfort business hotel",
                    area="Transit-connected district",
                    category="value hotel",
                    nightly_estimate=round((budget * 0.28) / max(days, 1), 2),
                    why_it_fits="Balances price and access when the itinerary has multiple cross-city moves.",
                    booking_tip="Check cancellation terms and room size before paying.",
                ),
                HotelRecommendation(
                    name=f"{destination} premium neighborhood stay",
                    area="Dining and shopping cluster",
                    category="premium hotel",
                    nightly_estimate=round((budget * 0.46) / max(days, 1), 2),
                    why_it_fits="Works well when comfort and evening walkability matter more than saving every rupee.",
                    booking_tip="Book early for weekend dates and festival periods.",
                ),
                HotelRecommendation(
                    name=f"{destination} serviced apartment option",
                    area="Residential pocket near cafes",
                    category="apartment",
                    nightly_estimate=round((budget * 0.32) / max(days, 1), 2),
                    why_it_fits=f"Useful for {traveler_label} who want more space, laundry access, or flexible meal timing.",
                    booking_tip="Confirm check-in process and exact neighborhood before booking.",
                ),
            ],
            local_places=[
                LocalPlace(
                    name="Neighborhood breakfast cafe",
                    area="Near your hotel base",
                    place_type="cafe",
                    best_time="Morning",
                    why_go=f"Easy first stop for {interest_b} and a low-stress start.",
                    estimated_cost=round(daily_base * 0.08, 2),
                ),
                LocalPlace(
                    name="Local market lane",
                    area="Old city or central market",
                    place_type="market",
                    best_time="Late morning",
                    why_go=f"Good for {interest_a}, snacks, and practical souvenir hunting.",
                    estimated_cost=round(daily_base * 0.1, 2),
                ),
                LocalPlace(
                    name="Sunset viewpoint",
                    area="Scenic district",
                    place_type="viewpoint",
                    best_time="Sunset",
                    why_go="Creates a strong anchor moment without inflating the budget.",
                    estimated_cost=round(daily_base * 0.05, 2),
                ),
            ],
            logistics=LogisticsPlan(
                arrival_transfer="Use a prepaid taxi, hotel transfer, or trusted ride-hailing pickup after arrival.",
                local_transport="Cluster each day by neighborhood and use ride-hailing for late evenings or long hops.",
                neighborhood_base="Choose a central area with restaurants, transit access, and safe evening movement.",
                booking_priorities=[
                    "Hotel with recent reviews",
                    "Any signature dining",
                    "Timed attraction entries",
                ],
                safety_notes=[
                    "Keep buffer time for traffic",
                    "Use verified transport at night",
                ],
                packing_notes=[
                    "Comfortable walking shoes",
                    "Portable charger",
                    "Weather-appropriate layer",
                ],
            ),
            attractions=[
                Attraction(
                    name=f"{destination} signature viewpoint",
                    reason="Delivers the iconic visual moment early in the trip.",
                    best_time="Sunset",
                    estimated_cost=round(budget * 0.04, 2),
                ),
                Attraction(
                    name="Local market district",
                    reason="Best single place to absorb food, color, and neighborhood personality.",
                    best_time="Late morning",
                    estimated_cost=round(budget * 0.03, 2),
                ),
                Attraction(
                    name="Creative quarter",
                    reason=f"Strong match for travelers who care about {interest_a} and more intimate discoveries.",
                    best_time="Golden hour",
                    estimated_cost=round(budget * 0.05, 2),
                ),
            ],
            itinerary=itinerary,
            cost_breakdown=cost_breakdown,
            smart_suggestions=[
                SmartSuggestion(
                    title="Mirror the stays you usually love",
                    description="Prioritize boutique hotels with textured interiors, walkable streets, and a strong breakfast program.",
                ),
                SmartSuggestion(
                    title="Lean into repeatable rituals",
                    description=f"Because your profile favors {interest_a} and {interest_b}, each day includes one low-pressure discovery window.",
                ),
                SmartSuggestion(
                    title="Keep the final day light",
                    description="Your memory pattern benefits from ending trips with flexible time rather than one last high-effort booking.",
                ),
            ],
        )
        self._integrate_plan_places_into_itinerary(
            result,
            destination=destination,
            mood=mood,
        )
        return self._attach_service_metadata(
            result,
            research=research,
            llm_mode="fallback",
            llm_error=error,
        )

    def _build_fallback_itinerary(
        self,
        *,
        destination: str,
        days: int,
        traveler_label: str,
        mood: str,
        interest_a: str,
        interest_b: str,
        daily_base: float,
        activity_cost: float,
        arrival_time: str,
    ) -> list[DayPlan]:
        theme_pool = [
            (
                "Arrival, orientation, and first taste",
                f"Settle into {destination} with a calm arrival rhythm designed for {traveler_label}, with easy logistics and a grounded neighborhood introduction.",
                [
                    (
                        "Arrival, transfer, and check-in",
                        arrival_time,
                        f"Central {destination}",
                        f"Reach the stay, freshen up, and keep the first day light for {traveler_label}.",
                        0.30,
                    ),
                    (
                        "Golden-hour neighborhood discovery",
                        "16:00",
                        "Creative district",
                        f"Walk independent streets to surface {interest_a}-led moments and local rhythm.",
                        0.20,
                    ),
                    (
                        "Signature dinner reservation",
                        "19:30",
                        "Chef-led restaurant",
                        f"Anchor the trip with a memorable {interest_b}-centric dinner experience that fits the group pace.",
                        0.50,
                    ),
                ],
                ["Cafe brunch with local pastries", "Late dinner tasting menu"],
            ),
            (
                "Immersive city texture",
                "Dive into the destination's most atmospheric corners with time for galleries, markets, and thoughtful pauses between neighborhoods.",
                [
                    (
                        "Morning architecture route",
                        "09:00",
                        "Historic core",
                        "Follow a compact route mixing iconic landmarks with side-street details.",
                        0.30,
                    ),
                    (
                        "Market tasting session",
                        "13:00",
                        "Local market hall",
                        "Sample regional bites and collect low-effort recommendations from vendors.",
                        0.30,
                    ),
                    (
                        "Twilight rooftop or waterfront pause",
                        "18:30",
                        "Scenic overlook",
                        "End the day with an unhurried viewpoint and soft social energy.",
                        0.40,
                    ),
                ],
                [
                    "Espresso and seasonal fruit",
                    "Market lunch crawl",
                    "Small-plates dinner",
                ],
            ),
            (
                f"{mood.capitalize()} signature day",
                f"Build the trip's emotional peak around curated {mood} energy, balancing spectacle with breathing room for {traveler_label}.",
                [
                    (
                        "Private or small-group highlight experience",
                        "09:30",
                        "Featured zone",
                        f"Prioritize the kind of experience that makes {destination} feel distinct rather than just popular.",
                        0.50,
                    ),
                    (
                        "Slow lunch near a cultural anchor",
                        "13:00",
                        "Museum quarter",
                        "Keep the middle of the day intentionally open to browse and linger.",
                        0.20,
                    ),
                    (
                        "Evening performance or cocktail salon",
                        "20:00",
                        "Nightlife district",
                        "Choose a polished evening venue aligned to the trip mood.",
                        0.30,
                    ),
                ],
                ["Hotel breakfast", "Leisurely lunch", "After-dark pairing menu"],
            ),
            (
                "Souvenirs, reflection, and departure",
                "Wrap with a low-friction final day that still leaves room for one more memorable neighborhood moment before departure.",
                [
                    (
                        "Breakfast and journaling stop",
                        "08:30",
                        "Design cafe",
                        "Use the final morning to lock in favorite addresses for a return visit.",
                        0.20,
                    ),
                    (
                        "Independent shopping loop",
                        "11:00",
                        "Artisan lane",
                        "Pick up tactile keepsakes from local makers instead of airport gifts.",
                        0.40,
                    ),
                    (
                        "Departure transfer",
                        "15:00",
                        "Airport or station",
                        f"Leave with cushion time and a smooth transfer plan for {traveler_label}.",
                        0.40,
                    ),
                ],
                ["Breakfast tasting board", "Farewell lunch"],
            ),
        ]

        itinerary: list[DayPlan] = []
        for day_number in range(1, days + 1):
            template = theme_pool[min(day_number - 1, len(theme_pool) - 1)]
            title, summary, activities_seed, meals = template
            day_multiplier = (
                0.82
                if day_number == 1
                else 0.9 if day_number == days else 1.12 if day_number % 2 == 0 else 1.0
            )
            if day_number > len(theme_pool):
                title = f"Extended {mood.capitalize()} discovery day {day_number}"
                summary = (
                    f"Use this added day to slow the pace, deepen {interest_a} and {interest_b} discoveries, "
                    f"and keep the plan comfortable for {traveler_label}."
                )
            activities = [
                Activity(
                    title=activity_title,
                    time=activity_time,
                    location=location,
                    description=description,
                    estimated_cost=round(activity_cost * weight, 2),
                )
                for activity_title, activity_time, location, description, weight in activities_seed
            ]
            target_count = self._target_activity_count(
                day_number=day_number,
                total_days=days,
                mood=mood,
            )
            mood_terms = MOOD_STRUCTURAL_SIGNALS.get(mood, {}).get("activity", {mood})
            emphasis = sorted(mood_terms)[0]
            while len(activities) < target_count:
                extra_index = len(activities) + 1
                activities.append(
                    self._build_extra_activity(
                        day_number=day_number,
                        activity_number=extra_index,
                        destination=destination,
                        mood=mood,
                        emphasis=emphasis,
                        estimated_cost=round(activity_cost * 0.16, 2),
                    )
                )
            itinerary.append(
                DayPlan(
                    day=day_number,
                    theme=title,
                    summary=summary,
                    activities=activities,
                    meals=list(meals),
                    daily_estimate=round(daily_base * day_multiplier, 2),
                )
            )
        return itinerary

    def _traveler_phrase(self, traveler_count: int) -> str:
        if traveler_count == 1:
            return "1 traveler"
        if traveler_count == 2:
            return "2 travelers"
        return f"{traveler_count} travelers"

    def _destination_markers(self, destination: str) -> list[str]:
        cleaned = destination.strip().lower()
        markers: list[str] = []
        if cleaned:
            markers.append(cleaned)
        for segment in cleaned.split(","):
            normalized_segment = " ".join(segment.split())
            if normalized_segment and normalized_segment not in markers:
                markers.append(normalized_segment)
        return markers

    def _matches_destination(
        self, search_haystack: str, destination_markers: list[str]
    ) -> bool:
        if not destination_markers:
            return True
        if destination_markers[0] in search_haystack:
            return True

        component_matches = sum(
            1 for marker in destination_markers[1:] if marker in search_haystack
        )
        if len(destination_markers) > 2:
            return component_matches >= 2
        return component_matches >= 1

    def _is_transient_provider_error(self, exc: Exception) -> bool:
        message = str(exc).upper()
        transient_markers = {
            "429",
            "503",
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "DEADLINE_EXCEEDED",
            "TIMEOUT",
            "HIGH DEMAND",
            "TRY AGAIN LATER",
        }
        return any(marker in message for marker in transient_markers)

    def _is_provider_quota_error(self, exc: Exception) -> bool:
        message = str(exc).upper()
        quota_markers = {
            "429",
            "QUOTA",
            "RATE LIMIT",
            "RATE_LIMIT",
            "RESOURCE_EXHAUSTED",
            "FREE_TIER",
            "LIMIT: 0",
        }
        return any(marker in message for marker in quota_markers)

    def _public_provider_error(self, exc: Exception) -> str:
        message = str(exc)
        upper_message = message.upper()
        if "GEMINI API ERROR 429" in upper_message or "QUOTA" in upper_message:
            return (
                "Gemini quota or rate limit was reached. TravelCraft tried the configured live providers "
                "and used the local planner because no live provider completed successfully."
            )
        if "GROQ API ERROR 429" in upper_message:
            return (
                "Groq rate limit was reached. TravelCraft tried the configured live providers "
                "and used the local planner because no live provider completed successfully."
            )
        if (
            "GROK/XAI API ERROR 429" in upper_message
            or "XAI API ERROR 429" in upper_message
        ):
            return (
                "Grok/xAI rate limit was reached. TravelCraft tried the configured live providers "
                "and used the local planner because no live provider completed successfully."
            )
        return self._truncate_for_log(message, 260)

    def _generate_with_openai_compatible(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        destination: str,
        days: int,
        budget: float,
    ) -> TripPlanLLMOutput:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=45.0, headers=headers) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                json=self._build_openai_compatible_payload(
                    model_name=model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    use_json_mode=True,
                ),
            )
            if response.status_code >= 400:
                detail = self._safe_response_text(response)
                if (
                    response.status_code == 400
                    and "FAILED TO VALIDATE JSON" in detail.upper()
                ):
                    logger.warning(
                        "%s JSON mode validation failed; retrying with local JSON parsing fallback.",
                        provider_name,
                    )
                    response = client.post(
                        f"{base_url}/chat/completions",
                        json=self._build_openai_compatible_payload(
                            model_name=model_name,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            use_json_mode=False,
                        ),
                    )
                    if response.status_code >= 400:
                        detail = self._safe_response_text(response)
                        raise RuntimeError(
                            f"{provider_name} API error {response.status_code}: {detail or 'Unknown error'}"
                        )
                else:
                    raise RuntimeError(
                        f"{provider_name} API error {response.status_code}: {detail or 'Unknown error'}"
                    )

        raw = response.json()
        message = raw.get("choices", [{}])[0].get("message", {})
        content = self._normalize_provider_content(message.get("content"))
        if not content:
            raise RuntimeError(
                f"{provider_name} returned no structured JSON output. Raw response shape: "
                + self._truncate_for_log(json.dumps(raw, ensure_ascii=True))
            )
        parsed_content = self._extract_json_object(content)
        normalized_content = self._normalize_trip_plan_payload(
            parsed_content,
            destination=destination,
            days=days,
            budget=budget,
        )
        return TripPlanLLMOutput.model_validate(normalized_content)

    def _generate_with_groq(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        destination: str,
        days: int,
        budget: float,
    ) -> TripPlanLLMOutput:
        return self._generate_with_openai_compatible(
            provider_name="Groq",
            base_url=self.groq_base_url,
            api_key=self.groq_api_key,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            destination=destination,
            days=days,
            budget=budget,
        )

    def _generate_with_gemini(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        destination: str,
        days: int,
        budget: float,
    ) -> TripPlanLLMOutput:
        prompt = (
            f"{system_prompt}\n\n{user_prompt}\n\n"
            "Return one complete JSON object only. Do not use markdown fences. "
            "Top-level keys: overview, best_time_to_visit, live_insights, customization, "
            "hotel_recommendations, local_places, logistics, attractions, itinerary, "
            "cost_breakdown, smart_suggestions."
        )
        url = f"{self.gemini_base_url}/models/{model_name}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.55,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.gemini_api_key,
        }
        with httpx.Client(timeout=60.0, headers=headers) as client:
            response = client.post(url, json=payload)
            if response.status_code >= 400:
                detail = self._safe_response_text(response)
                raise RuntimeError(
                    f"Gemini API error {response.status_code}: {detail or 'Unknown error'}"
                )

        raw = response.json()
        content = self._extract_gemini_text(raw)
        if not content:
            raise RuntimeError(
                "Gemini returned no structured JSON output. Raw response shape: "
                + self._truncate_for_log(json.dumps(raw, ensure_ascii=True))
            )
        parsed_content = self._extract_json_object(content)
        normalized_content = self._normalize_trip_plan_payload(
            parsed_content,
            destination=destination,
            days=days,
            budget=budget,
        )
        return TripPlanLLMOutput.model_validate(normalized_content)

    def _extract_gemini_text(self, payload: dict[str, Any]) -> str:
        parts: list[str] = []
        for candidate in payload.get("candidates", []):
            content = candidate.get("content") if isinstance(candidate, dict) else None
            for part in (content or {}).get("parts", []):
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        return "\n".join(part.strip() for part in parts if part.strip())

    def _build_openai_compatible_payload(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        use_json_mode: bool,
    ) -> dict[str, Any]:
        combined_prompt = (
            f"{system_prompt}\n\n"
            f"{user_prompt}\n\n"
            "Output requirements:\n"
            "- Return only JSON.\n"
            "- Do not wrap the JSON in markdown fences.\n"
            "- Include these top-level keys exactly: overview, best_time_to_visit, live_insights, customization, hotel_recommendations, local_places, logistics, attractions, itinerary, cost_breakdown, smart_suggestions.\n"
            "- attractions must be an array of exactly 3 objects with: name, reason, best_time, estimated_cost.\n"
            "- hotel_recommendations must include: name, area, category, nightly_estimate, why_it_fits, booking_tip.\n"
            "- local_places must include: name, area, place_type, best_time, why_go, estimated_cost.\n"
            "- logistics must include: arrival_transfer, local_transport, neighborhood_base, booking_priorities, safety_notes, packing_notes.\n"
            "- customization must include: pace, accommodation_style, food_preference, must_include, avoid.\n"
            "- itinerary must be an array of day objects with: day, theme, summary, activities, meals, daily_estimate.\n"
            "- each activity must include: title, time, location, description, estimated_cost.\n"
            "- cost_breakdown must include: accommodation, food, transport, activities, contingency, total.\n"
            "- smart_suggestions must be an array of objects with: title, description.\n"
            "- The JSON must be complete and valid.\n"
        )
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": combined_prompt,
                }
            ],
            "temperature": 0.6,
            "max_completion_tokens": 4000,
        }
        if use_json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _safe_response_text(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error_payload = payload.get("error")
                if isinstance(error_payload, dict):
                    message = error_payload.get("message")
                    if message:
                        return str(message)
                return json.dumps(payload)
        except Exception:
            pass

        try:
            return response.text
        except Exception:
            return ""

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        if start != -1:
            decoder = json.JSONDecoder()
            try:
                parsed, _end_index = decoder.raw_decode(cleaned[start:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Provider returned invalid JSON: {exc}") from exc

        raise RuntimeError("Provider did not return a valid JSON object.")

    def _normalize_trip_plan_payload(
        self,
        payload: dict[str, Any],
        *,
        destination: str,
        days: int,
        budget: float,
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = dict(payload)
        normalized["overview"] = self._string_or_default(
            normalized.get("overview"),
            f"A refined trip through {destination}.",
        )
        normalized["best_time_to_visit"] = self._string_or_default(
            normalized.get("best_time_to_visit"),
            "Year-round with the smoothest experience during the shoulder season.",
        )
        normalized["live_insights"] = self._normalize_string_list(
            normalized.get("live_insights")
        )
        normalized["customization"] = self._normalize_customization(
            normalized.get("customization")
        )
        normalized["hotel_recommendations"] = self._normalize_hotels(
            normalized.get("hotel_recommendations")
        )
        normalized["local_places"] = self._normalize_local_places(
            normalized.get("local_places")
        )
        normalized["logistics"] = self._normalize_logistics(normalized.get("logistics"))
        normalized["attractions"] = self._normalize_attractions(
            normalized.get("attractions")
        )
        normalized["itinerary"] = self._normalize_itinerary(
            normalized.get("itinerary"), days
        )
        normalized["smart_suggestions"] = self._normalize_suggestions(
            normalized.get("smart_suggestions")
        )
        normalized["cost_breakdown"] = self._normalize_cost_breakdown(
            normalized.get("cost_breakdown"),
            itinerary=normalized["itinerary"],
            attractions=normalized["attractions"],
            budget=budget,
        )
        return normalized

    def _normalize_customization(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raw = {}
        return {
            "pace": self._string_or_default(raw.get("pace"), "balanced"),
            "accommodation_style": self._string_or_default(
                raw.get("accommodation_style"), "mixed"
            ),
            "food_preference": self._string_or_default(
                raw.get("food_preference"), "local favorites"
            ),
            "must_include": self._normalize_string_list(raw.get("must_include")),
            "avoid": self._normalize_string_list(raw.get("avoid")),
        }

    def _normalize_hotels(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        hotels: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            hotels.append(
                {
                    "name": self._string_or_default(
                        item.get("name"), "Recommended stay"
                    ),
                    "area": self._string_or_default(item.get("area"), "Central area"),
                    "category": self._string_or_default(item.get("category"), "hotel"),
                    "nightly_estimate": self._money_to_float(
                        item.get("nightly_estimate")
                    ),
                    "why_it_fits": self._string_or_default(
                        item.get("why_it_fits"), "A practical fit for this trip."
                    ),
                    "booking_tip": self._string_or_default(
                        item.get("booking_tip"),
                        "Compare recent reviews before booking.",
                    ),
                }
            )
        return hotels[:5]

    def _normalize_local_places(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        places: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    places.append(
                        {
                            "name": cleaned,
                            "area": "Nearby",
                            "place_type": "local pick",
                            "best_time": "Flexible",
                            "why_go": cleaned,
                            "estimated_cost": 0.0,
                        }
                    )
                continue
            if not isinstance(item, dict):
                continue
            places.append(
                {
                    "name": self._string_or_default(
                        item.get("name")
                        or item.get("title")
                        or item.get("place_name"),
                        "Local place",
                    ),
                    "area": self._string_or_default(
                        item.get("area")
                        or item.get("location")
                        or item.get("neighborhood")
                        or item.get("district"),
                        "Nearby",
                    ),
                    "place_type": self._string_or_default(
                        item.get("place_type")
                        or item.get("type")
                        or item.get("category"),
                        "place",
                    ),
                    "best_time": self._string_or_default(
                        item.get("best_time")
                        or item.get("visit_time")
                        or item.get("recommended_time"),
                        "Flexible",
                    ),
                    "why_go": self._string_or_default(
                        item.get("why_go")
                        or item.get("description")
                        or item.get("reason")
                        or item.get("notes"),
                        "Worth adding to the plan.",
                    ),
                    "estimated_cost": self._money_to_float(
                        item.get("estimated_cost")
                        or item.get("cost")
                        or item.get("price")
                        or item.get("entry_fee")
                    ),
                }
            )
        return places[:8]

    def _normalize_logistics(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raw = {}
        return {
            "arrival_transfer": self._string_or_default(
                raw.get("arrival_transfer"),
                "Use a prepaid taxi or trusted ride-hailing option on arrival.",
            ),
            "local_transport": self._string_or_default(
                raw.get("local_transport"),
                "Use a mix of walking, ride-hailing, and public transit where reliable.",
            ),
            "neighborhood_base": self._string_or_default(
                raw.get("neighborhood_base"),
                "Stay near a central, well-connected neighborhood.",
            ),
            "booking_priorities": self._normalize_string_list(
                raw.get("booking_priorities")
            ),
            "safety_notes": self._normalize_string_list(raw.get("safety_notes")),
            "packing_notes": self._normalize_string_list(raw.get("packing_notes")),
        }

    def _normalize_attractions(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        attractions: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            attractions.append(
                {
                    "name": self._string_or_default(
                        item.get("name"), "Featured attraction"
                    ),
                    "reason": self._string_or_default(
                        item.get("reason"), "Worth visiting."
                    ),
                    "best_time": self._string_or_default(
                        item.get("best_time"), "Flexible"
                    ),
                    "estimated_cost": self._money_to_float(item.get("estimated_cost")),
                }
            )
        return attractions

    def _normalize_itinerary(self, raw: Any, days: int) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []

        itinerary: list[dict[str, Any]] = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            activities = self._normalize_activities(item.get("activities"))
            meals = self._normalize_meals(item.get("meals"))
            daily_estimate = self._money_to_float(item.get("daily_estimate"))
            if daily_estimate <= 0:
                daily_estimate = round(
                    sum(activity["estimated_cost"] for activity in activities), 2
                )
            itinerary.append(
                {
                    "day": int(item.get("day") or index),
                    "theme": self._string_or_default(item.get("theme"), f"Day {index}"),
                    "summary": self._string_or_default(
                        item.get("summary"), f"Day {index} in the destination."
                    ),
                    "activities": activities,
                    "meals": meals,
                    "daily_estimate": daily_estimate,
                }
            )

        return itinerary[:days]

    def _normalize_activities(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        activities: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    activities.append(
                        {
                            "title": cleaned,
                            "time": "Flexible",
                            "location": "Destination",
                            "description": cleaned,
                            "estimated_cost": 0.0,
                        }
                    )
                continue
            if not isinstance(item, dict):
                continue
            title = self._string_or_default(
                item.get("title")
                or item.get("name")
                or item.get("activity")
                or item.get("activity_name"),
                "Planned activity",
            )
            location = self._string_or_default(
                item.get("location")
                or item.get("place")
                or item.get("area")
                or item.get("venue"),
                "Destination",
            )
            description = self._string_or_default(
                item.get("description")
                or item.get("details")
                or item.get("notes")
                or item.get("summary"),
                "A relevant stop for the trip.",
            )
            activities.append(
                {
                    "title": title,
                    "time": self._string_or_default(
                        item.get("time") or item.get("start_time"), "Flexible"
                    ),
                    "location": location,
                    "description": description,
                    "estimated_cost": self._money_to_float(
                        item.get("estimated_cost")
                        or item.get("cost")
                        or item.get("price")
                    ),
                }
            )
        return activities

    def _normalize_meals(self, raw: Any) -> list[str]:
        if not isinstance(raw, list):
            return []
        meals: list[str] = []
        for item in raw:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    meals.append(cleaned)
                continue
            if isinstance(item, dict):
                name = self._string_or_default(item.get("name"), "Meal")
                location = self._string_or_default(item.get("location"), "")
                description = self._string_or_default(item.get("description"), "")
                detail = location or description
                meals.append(f"{name} - {detail}".strip(" -"))
        return meals

    def _normalize_suggestions(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        suggestions: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    suggestions.append({"title": cleaned[:80], "description": cleaned})
                continue
            if isinstance(item, dict):
                suggestions.append(
                    {
                        "title": self._string_or_default(
                            item.get("title"), "Helpful suggestion"
                        ),
                        "description": self._string_or_default(
                            item.get("description"),
                            "A useful suggestion for this trip.",
                        ),
                    }
                )
        return suggestions

    def _normalize_cost_breakdown(
        self,
        raw: Any,
        *,
        itinerary: list[dict[str, Any]],
        attractions: list[dict[str, Any]],
        budget: float,
    ) -> dict[str, float]:
        inferred_activity_total = round(
            sum(
                activity["estimated_cost"]
                for day in itinerary
                for activity in day["activities"]
            )
            + sum(attraction["estimated_cost"] for attraction in attractions),
            2,
        )
        inferred_breakdown = {
            "accommodation": round(budget * 0.36, 2),
            "food": round(budget * 0.2, 2),
            "transport": round(budget * 0.12, 2),
            "activities": round(inferred_activity_total or budget * 0.24, 2),
        }
        inferred_breakdown["contingency"] = round(
            max(
                budget
                - (
                    inferred_breakdown["accommodation"]
                    + inferred_breakdown["food"]
                    + inferred_breakdown["transport"]
                    + inferred_breakdown["activities"]
                ),
                0,
            ),
            2,
        )
        if isinstance(raw, dict):
            accommodation = self._money_to_float(
                raw.get("accommodation")
                or raw.get("hotel")
                or raw.get("hotels")
                or raw.get("stay")
                or raw.get("lodging")
                or raw.get("accommodation_cost")
                or raw.get("hotel_cost")
            )
            food = self._money_to_float(
                raw.get("food")
                or raw.get("meals")
                or raw.get("dining")
                or raw.get("food_cost")
                or raw.get("food_budget")
            )
            transport = self._money_to_float(
                raw.get("transport")
                or raw.get("transportation")
                or raw.get("travel")
                or raw.get("local_transport")
                or raw.get("transport_cost")
            )
            activities = self._money_to_float(
                raw.get("activities")
                or raw.get("sightseeing")
                or raw.get("experiences")
                or raw.get("experience_cost")
                or raw.get("activity_cost")
            )
            contingency = self._money_to_float(
                raw.get("contingency")
                or raw.get("misc")
                or raw.get("miscellaneous")
                or raw.get("buffer")
            )
            total = self._money_to_float(raw.get("total"))
            if total <= 0:
                total = round(budget, 2)
            if accommodation <= 0:
                accommodation = inferred_breakdown["accommodation"]
            if food <= 0:
                food = inferred_breakdown["food"]
            if transport <= 0:
                transport = inferred_breakdown["transport"]
            if activities <= 0:
                activities = inferred_breakdown["activities"]
            if contingency <= 0:
                contingency = round(
                    max(total - (accommodation + food + transport + activities), 0), 2
                )
            return {
                "accommodation": accommodation,
                "food": food,
                "transport": transport,
                "activities": activities,
                "contingency": contingency,
                "total": total,
            }

        return {
            "accommodation": inferred_breakdown["accommodation"],
            "food": inferred_breakdown["food"],
            "transport": inferred_breakdown["transport"],
            "activities": inferred_breakdown["activities"],
            "contingency": inferred_breakdown["contingency"],
            "total": round(budget, 2),
        }

    def _normalize_string_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        return []

    def _string_or_default(self, value: Any, default: str) -> str:
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return default

    def _money_to_float(self, value: Any) -> float:
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return 0.0
            if cleaned.lower() in {"free", "no cost", "complimentary"}:
                return 0.0
            match = re.search(r"-?\d[\d,]*(?:\.\d+)?", cleaned.replace("₹", ""))
            if match:
                try:
                    return round(float(match.group(0).replace(",", "")), 2)
                except ValueError:
                    return 0.0
        return 0.0

    def _normalize_provider_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
                        continue
                    if item.get("type") == "text":
                        nested_text = item.get("content")
                        if isinstance(nested_text, str):
                            parts.append(nested_text)
            return "\n".join(part.strip() for part in parts if part and part.strip())
        return ""

    def _truncate_for_log(self, value: str, limit: int = 500) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    def _attach_service_metadata(
        self,
        result: TripPlanLLMOutput,
        *,
        research: dict[str, Any],
        llm_mode: str,
        llm_error: str | None,
    ) -> TripPlanLLMOutput:
        result.research_mode = research.get("mode", "fallback")
        result.research_error = research.get("error")
        result.research_sources = [
            (
                source
                if isinstance(source, ResearchSource)
                else ResearchSource.model_validate(source)
            )
            for source in research.get("sources", [])
        ]
        result.llm_mode = llm_mode
        result.llm_error = llm_error
        return result
