from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db_models import (
    DestinationResearch,
    ItineraryDay,
    ItineraryItem,
    MemoryEvent,
    TravelPlan,
    Trip,
    User,
    UserPreference,
)
from app.models import (
    Activity,
    Attraction,
    CostBreakdown,
    CustomizationSummary,
    DayPlan,
    GenerateTripRequest,
    HotelRecommendation,
    LocalPlace,
    LogisticsPlan,
    PastTrip,
    ResearchSource,
    SmartSuggestion,
    TripPlanResponse,
    UpdateMemoryRequest,
    UserMemory,
)


API_TRIP_MOODS = {"relaxed", "adventure", "luxury"}
CANONICAL_TRAVEL_STYLES = {"budget", "balanced", "premium", "luxury"}
APP_CURRENCY_CODE = "INR"


class MemoryService:
    def get_trip(self, db: Session, user: User, trip_id: str) -> PastTrip | None:
        trip = db.scalar(
            select(Trip)
            .where(Trip.user_id == user.id, Trip.legacy_trip_key == trip_id)
            .options(
                selectinload(Trip.travel_plan)
                .selectinload(TravelPlan.itinerary_days)
                .selectinload(ItineraryDay.items),
                selectinload(Trip.research_documents),
                selectinload(Trip.user).selectinload(User.preference),
            )
        )
        if not trip or not trip.travel_plan:
            return None
        return self._serialize_trip(trip)

    def load_memory(self, db: Session, user: User) -> UserMemory:
        preference = self._ensure_preference(db, user)
        trips = list(
            db.scalars(
                select(Trip)
                .outerjoin(TravelPlan)
                .where(Trip.user_id == user.id)
                .options(
                    selectinload(Trip.travel_plan)
                    .selectinload(TravelPlan.itinerary_days)
                    .selectinload(ItineraryDay.items),
                    selectinload(Trip.research_documents),
                )
                .order_by(desc(func.coalesce(TravelPlan.generated_at, Trip.created_at)))
                .limit(8)
            )
        )
        recent_events = list(
            db.scalars(
                select(MemoryEvent)
                .where(MemoryEvent.user_id == user.id)
                .order_by(desc(MemoryEvent.recorded_at))
                .limit(5)
            )
        )

        memory = UserMemory(
            name=user.name,
            bio=preference.bio,
            home_airport=preference.home_airport,
            budget_preference=self._collapse_budget(preference),
            travel_style=preference.travel_style_notes or preference.travel_style,
            interests=list(preference.interests or []),
            preferred_mood=self._normalize_api_mood(preference.trip_mood),
            past_trips=[self._serialize_trip(trip) for trip in trips if trip.travel_plan],
        )
        memory.insights = self._derive_insights(memory, recent_events)
        return memory

    def update_memory(self, db: Session, user: User, payload: UpdateMemoryRequest) -> UserMemory:
        preference = self._ensure_preference(db, user)
        updates = payload.model_dump(exclude_none=True)
        events: list[MemoryEvent] = []

        if "name" in updates:
            new_name = updates.pop("name").strip()
            if new_name and new_name != user.name:
                user.name = new_name

        for key, value in updates.items():
            if key == "budget_preference":
                old_value = self._collapse_budget(preference)
                preference.budget_min = value
                preference.budget_max = value
                events.append(self._build_event(user.id, None, "budget_preference", old_value, value))
                continue

            if key == "preferred_mood":
                old_value = preference.trip_mood
                preference.trip_mood = value
                events.append(self._build_event(user.id, None, "preferred_mood", old_value, value))
                continue

            if key == "travel_style":
                old_value = preference.travel_style_notes or preference.travel_style
                canonical = self._canonicalize_travel_style(value)
                preference.travel_style = canonical
                preference.travel_style_notes = value.strip()
                events.append(self._build_event(user.id, None, "travel_style", old_value, value.strip()))
                continue

            if key == "interests":
                old_value = list(preference.interests or [])
                new_value = [item.strip() for item in value if item.strip()]
                preference.interests = new_value
                events.append(self._build_event(user.id, None, "interests", old_value, new_value))
                continue

            old_value = getattr(preference, key)
            setattr(preference, key, value)
            events.append(self._build_event(user.id, None, key, old_value, value))

        db.add_all([user, preference, *events])
        db.commit()
        db.refresh(user)
        db.refresh(preference)
        return self.load_memory(db, user)

    def store_generated_trip(
        self,
        db: Session,
        user: User,
        request: GenerateTripRequest,
        plan: TripPlanResponse,
    ) -> UserMemory:
        preference = self._ensure_preference(db, user)
        preference.budget_min = request.budget
        preference.budget_max = request.budget
        preference.interests = [item.strip() for item in request.interests if item.strip()]
        preference.trip_mood = request.mood

        trip = Trip(
            legacy_trip_key=plan.trip_id,
            user_id=user.id,
            title=self._build_trip_title(plan.destination, request.mood),
            destination=plan.destination,
            destination_country="",
            origin_airport=preference.home_airport,
            budget=plan.budget,
            currency_code=APP_CURRENCY_CODE,
            status="planned",
            notes=plan.overview,
            traveler_count=request.traveler_count,
        )

        plan_payload = plan.model_dump(mode="json")
        travel_plan = TravelPlan(
            trip=trip,
            generated_by_model=settings.groq_model if plan.llm_mode == "live" else "fallback-template",
            generation_provider="groq" if plan.llm_mode == "live" else "fallback",
            prompt_snapshot={
                "submitted_request": request.model_dump(mode="json"),
                "destination": request.destination,
                "days": request.days,
                "arrival_time": request.arrival_time,
                "traveler_count": request.traveler_count,
                "budget": request.budget,
                "interests": request.interests,
                "mood": request.mood,
                "memory": {
                    "home_airport": preference.home_airport,
                    "travel_style": preference.travel_style_notes or preference.travel_style,
                    "interests": preference.interests,
                },
            },
            ai_output=plan_payload,
            overview=plan.overview,
            best_time_to_visit=plan.best_time_to_visit,
            cost_estimation=plan.cost_breakdown.model_dump(mode="json"),
            source_data={
                "live_insights": plan.live_insights,
                "research_mode": plan.research_mode,
                "research_sources": [source.model_dump(mode="json") for source in plan.research_sources],
            },
            research_mode=plan.research_mode,
            llm_mode=plan.llm_mode,
            research_error=plan.research_error,
            llm_error=plan.llm_error,
            generated_at=self._parse_datetime(plan.generated_at),
        )

        day_models = self._build_itinerary_days(travel_plan, plan)

        db.add_all([preference, trip, travel_plan, *day_models])
        db.flush()

        research_rows = self._build_research_rows(trip, plan)
        events = [
            self._build_trip_event(user.id, trip.id, plan.trip_id, request),
            self._build_event(user.id, trip.id, "preferred_mood", None, request.mood),
        ]

        db.add_all([*research_rows, *events])
        db.commit()
        return self.load_memory(db, user)

    def _ensure_preference(self, db: Session, user: User) -> UserPreference:
        preference = user.preference
        if preference:
            return preference

        preference = UserPreference(
            user_id=user.id,
            bio="",
            budget_min=None,
            budget_max=None,
            interests=[],
            travel_style="balanced",
            travel_style_notes="",
            trip_mood="relaxed",
            preferred_transport="mixed",
            accommodation_type="mixed",
            home_airport="",
            language_preferences=[],
            dietary_preferences=[],
            accessibility_needs={},
        )
        db.add(preference)
        db.commit()
        db.refresh(preference)
        return preference

    def _serialize_trip(self, trip: Trip) -> PastTrip:
        travel_plan = trip.travel_plan
        ai_output = dict(travel_plan.ai_output or {}) if travel_plan else {}

        return PastTrip(
            overview=travel_plan.overview,
            best_time_to_visit=travel_plan.best_time_to_visit,
            live_insights=list(ai_output.get("live_insights") or self._build_live_insights(travel_plan)),
            customization=CustomizationSummary(**(ai_output.get("customization") or {})),
            hotel_recommendations=[HotelRecommendation(**item) for item in ai_output.get("hotel_recommendations", [])],
            local_places=[LocalPlace(**item) for item in ai_output.get("local_places", [])],
            logistics=LogisticsPlan(**(ai_output.get("logistics") or {})),
            attractions=self._build_attractions(ai_output),
            itinerary=self._serialize_itinerary(travel_plan),
            cost_breakdown=self._build_cost_breakdown(ai_output, travel_plan),
            smart_suggestions=self._build_suggestions(ai_output),
            research_mode=travel_plan.research_mode,
            research_error=travel_plan.research_error,
            research_sources=self._serialize_research_sources(trip.research_documents, travel_plan),
            llm_mode=travel_plan.llm_mode,
            llm_error=travel_plan.llm_error,
            trip_id=trip.legacy_trip_key,
            destination=trip.destination,
            days=len(travel_plan.itinerary_days),
            traveler_count=trip.traveler_count,
            budget=trip.budget,
            currency_code=trip.currency_code,
            interests=list(ai_output.get("interests") or (trip.user.preference.interests if trip.user.preference else [])),
            mood=self._normalize_api_mood(
                ai_output.get("mood")
                or (trip.user.preference.trip_mood if trip.user.preference else "relaxed")
            ),
            generated_at=travel_plan.generated_at.isoformat(),
            highlight=self._extract_highlight(ai_output),
        )

    def _serialize_itinerary(self, travel_plan: TravelPlan) -> list[DayPlan]:
        days: list[DayPlan] = []
        for day in travel_plan.itinerary_days:
            activities: list[Activity] = []
            meals: list[str] = []
            for item in day.items:
                if item.item_type == "meal":
                    meals.append(item.title)
                    continue

                activities.append(
                    Activity(
                        title=item.title,
                        time=item.start_time.strftime("%H:%M") if item.start_time else "",
                        location=item.location_name,
                        description=str(item.details.get("description", "")),
                        estimated_cost=float(item.estimated_cost or 0),
                    )
                )

            days.append(
                DayPlan(
                    day=day.day_number,
                    theme=day.theme,
                    summary=day.summary,
                    activities=activities,
                    meals=meals,
                    daily_estimate=float(day.daily_budget_estimate or 0),
                )
            )
        return days

    def _serialize_research_sources(
        self,
        research_documents: list[DestinationResearch],
        travel_plan: TravelPlan,
    ) -> list[ResearchSource]:
        if research_documents:
            return [
                ResearchSource(
                    title=doc.title,
                    url=doc.source_url,
                    domain=doc.source_domain,
                    snippet=doc.summary_text,
                )
                for doc in research_documents
            ]

        source_rows = travel_plan.source_data.get("research_sources", []) if travel_plan.source_data else []
        return [ResearchSource(**row) for row in source_rows]

    def _build_itinerary_days(self, travel_plan: TravelPlan, plan: TripPlanResponse) -> list[ItineraryDay]:
        day_models: list[ItineraryDay] = []
        for day in plan.itinerary:
            day_model = ItineraryDay(
                travel_plan=travel_plan,
                day_number=day.day,
                theme=day.theme,
                summary=day.summary,
                daily_budget_estimate=day.daily_estimate,
            )
            item_models: list[ItineraryItem] = []
            sort_order = 1
            for activity in day.activities:
                item_models.append(
                    ItineraryItem(
                        sort_order=sort_order,
                        item_type="activity",
                        title=activity.title,
                        location_name=activity.location,
                        start_time=self._parse_time(activity.time),
                        estimated_cost=activity.estimated_cost,
                        booking_required=False,
                        tags=[],
                        details={"description": activity.description},
                    )
                )
                sort_order += 1
            for meal in day.meals:
                item_models.append(
                    ItineraryItem(
                        sort_order=sort_order,
                        item_type="meal",
                        title=meal,
                        location_name="",
                        estimated_cost=None,
                        booking_required=False,
                        tags=[],
                        details={},
                    )
                )
                sort_order += 1
            day_model.items = item_models
            day_models.append(day_model)
        return day_models

    def _build_research_rows(self, trip: Trip, plan: TripPlanResponse) -> list[DestinationResearch]:
        rows: list[DestinationResearch] = []
        for source in plan.research_sources:
            rows.append(
                DestinationResearch(
                    trip=trip,
                    source_url=source.url,
                    source_domain=source.domain,
                    content_type="guide",
                    title=source.title,
                    scraped_text="",
                    summary_text=source.snippet,
                    tags=[],
                    source_metadata=source.model_dump(mode="json"),
                    scraped_at=self._parse_datetime(plan.generated_at),
                )
            )
        return rows

    def _build_event(
        self,
        user_id: str,
        trip_id: str | None,
        event_key: str,
        old_value: Any,
        new_value: Any,
    ) -> MemoryEvent:
        return MemoryEvent(
            user_id=user_id,
            trip_id=trip_id,
            event_type="preference_update",
            event_key=event_key,
            event_value={"old": old_value, "new": new_value},
            source="user",
            confidence_score=1.0,
            recorded_at=datetime.now(timezone.utc),
        )

    def _build_trip_event(
        self,
        user_id: str,
        trip_id: str,
        trip_key: str,
        request: GenerateTripRequest,
    ) -> MemoryEvent:
        return MemoryEvent(
            user_id=user_id,
            trip_id=trip_id,
            event_type="trip_generation",
            event_key="trip_generation",
            event_value=request.model_dump(mode="json") | {"trip_id": trip_key},
            source="system",
            confidence_score=1.0,
            recorded_at=datetime.now(timezone.utc),
        )

    def _build_cost_breakdown(self, ai_output: dict[str, Any], travel_plan: TravelPlan) -> CostBreakdown:
        payload = ai_output.get("cost_breakdown") or travel_plan.cost_estimation or {}
        return CostBreakdown(**payload)

    def _build_attractions(self, ai_output: dict[str, Any]) -> list[Attraction]:
        return [Attraction(**item) for item in ai_output.get("attractions", [])]

    def _build_suggestions(self, ai_output: dict[str, Any]) -> list[SmartSuggestion]:
        return [SmartSuggestion(**item) for item in ai_output.get("smart_suggestions", [])]

    def _build_live_insights(self, travel_plan: TravelPlan) -> list[str]:
        return list(travel_plan.source_data.get("live_insights", [])) if travel_plan.source_data else []

    def _extract_highlight(self, ai_output: dict[str, Any]) -> str:
        attractions = ai_output.get("attractions") or []
        if attractions:
            return str(attractions[0].get("name", "Curated city highlights"))
        return "Curated city highlights"

    def _derive_insights(self, memory: UserMemory, recent_events: list[MemoryEvent]) -> list[str]:
        insights: list[str] = []

        if memory.budget_preference is not None:
            insights.append(
                f"Average stored budget preference is {self._format_currency(memory.budget_preference)}, which points to your current comfort range."
            )
        else:
            insights.append("Set a budget preference to help TravelCraft tune price-sensitive recommendations.")

        if memory.interests:
            insights.append(f"Top recurring interests: {', '.join(memory.interests[:3])}.")
        else:
            insights.append("Add a few interests so future itineraries can prioritize the right neighborhoods and experiences.")

        insights.append(
            f"Current preferred trip mood is {memory.preferred_mood}, shaping how itineraries pace energy across the day."
        )

        if memory.past_trips:
            last_trip = memory.past_trips[0]
            insights.append(
                f"Your latest memory is {last_trip.destination}, suggesting fresh appetite for {last_trip.mood} escapes."
            )
        elif recent_events:
            insights.append("Your preference memory is live, and the next generated trip will start teaching the planner your patterns.")
        else:
            insights.append("Generate your first trip to start building smart suggestions from your own history.")

        return insights

    def _collapse_budget(self, preference: UserPreference) -> float | None:
        if preference.budget_min is None and preference.budget_max is None:
            return None
        if preference.budget_min is None:
            return preference.budget_max
        if preference.budget_max is None:
            return preference.budget_min
        return round((preference.budget_min + preference.budget_max) / 2, 2)

    def _format_currency(self, amount: float | None) -> str:
        if amount is None:
            return f"{APP_CURRENCY_CODE} 0"
        rounded = round(float(amount), 2)
        if rounded.is_integer():
            return f"{APP_CURRENCY_CODE} {int(rounded):,}"
        return f"{APP_CURRENCY_CODE} {rounded:,.2f}"

    def _canonicalize_travel_style(self, value: str) -> str:
        lowered = value.strip().lower()
        if lowered in CANONICAL_TRAVEL_STYLES:
            return lowered
        if any(term in lowered for term in ("luxury", "boutique", "premium")):
            return "luxury" if "luxury" in lowered else "premium"
        if any(term in lowered for term in ("budget", "affordable", "cheap")):
            return "budget"
        return "balanced"

    def _normalize_api_mood(self, mood: str) -> str:
        return mood if mood in API_TRIP_MOODS else "relaxed"

    def _build_trip_title(self, destination: str, mood: str) -> str:
        return f"{destination} {mood.capitalize()} Plan"

    def _parse_time(self, value: str) -> time | None:
        value = value.strip()
        if not value:
            return None
        for fmt in ("%H:%M", "%I:%M %p", "%I %p"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
        return None

    def _parse_datetime(self, value: str) -> datetime:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
