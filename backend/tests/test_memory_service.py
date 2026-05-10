from __future__ import annotations

from datetime import datetime, timezone

from app.db_models import User, UserPreference
from app.models import (
    Activity,
    Attraction,
    CostBreakdown,
    DayPlan,
    GenerateTripRequest,
    ResearchSource,
    SmartSuggestion,
    TripPlanResponse,
)
from app.services.memory_service import MemoryService


class FakeSession:
    def __init__(self) -> None:
        self.added_batches: list[list[object]] = []

    def add(self, _obj: object) -> None:
        return None

    def add_all(self, objs: list[object]) -> None:
        self.added_batches.append(list(objs))

    def commit(self) -> None:
        return None

    def flush(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None


def test_store_generated_trip_preserves_currency_and_prompt_snapshot(monkeypatch) -> None:
    service = MemoryService()
    fake_db = FakeSession()
    user = User(id="user-1", email="user@example.com", password_hash="hash", name="Traveler")
    preference = UserPreference(
        user_id="user-1",
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
    user.preference = preference

    request = GenerateTripRequest(
        destination="Tokyo",
        days=5,
        traveler_count=3,
        budget=150,
        currency_code="INR",
        interests=["food"],
        mood="relaxed",
    )
    plan = TripPlanResponse(
        trip_id="trip-1",
        destination="Tokyo",
        days=5,
        traveler_count=3,
        budget=150,
        currency_code="INR",
        interests=["food"],
        mood="relaxed",
        generated_at=datetime.now(timezone.utc).isoformat(),
        overview="Tokyo relaxed food plan.",
        best_time_to_visit="Spring",
        live_insights=[],
        attractions=[Attraction(name="Tsukiji", reason="Food focus", best_time="Morning", estimated_cost=10)],
        itinerary=[
            DayPlan(
                day=1,
                theme="Arrival",
                summary="Relaxed start",
                activities=[
                    Activity(title="Food crawl", time="10:00", location="Market", description="Food focus", estimated_cost=10),
                    Activity(title="Cafe stop", time="13:00", location="Cafe", description="Slow break", estimated_cost=5),
                    Activity(title="Sunset walk", time="18:00", location="River", description="Relaxed walk", estimated_cost=0),
                ],
                meals=["Breakfast", "Dinner"],
                daily_estimate=15,
            )
        ]
        * 4,
        cost_breakdown=CostBreakdown(accommodation=60, food=30, transport=20, activities=25, contingency=15, total=150),
        smart_suggestions=[SmartSuggestion(title="Food first", description="Keep food central.")],
        research_sources=[ResearchSource(title="Guide", url="https://example.com", domain="example.com", snippet="Tokyo food")],
    )

    monkeypatch.setattr(service, "load_memory", lambda db, current_user: {"ok": True})

    service.store_generated_trip(fake_db, user, request, plan)

    persisted_objects = [obj for batch in fake_db.added_batches for obj in batch]
    trip = next(obj for obj in persisted_objects if obj.__class__.__name__ == "Trip")
    travel_plan = next(obj for obj in persisted_objects if obj.__class__.__name__ == "TravelPlan")

    assert trip.currency_code == "INR"
    assert trip.traveler_count == 3
    assert travel_plan.prompt_snapshot["submitted_request"]["currency_code"] == "INR"
    assert travel_plan.prompt_snapshot["submitted_request"]["days"] == 5
    assert travel_plan.prompt_snapshot["submitted_request"]["traveler_count"] == 3
