from __future__ import annotations

import json

from app.models import (
    Activity,
    Attraction,
    CostBreakdown,
    DayPlan,
    HotelRecommendation,
    LocalPlace,
    SmartSuggestion,
    TripPlanLLMOutput,
)
from app.services.llm_service import LLMService


def build_plan(*, mood: str = "relaxed", interest: str = "food") -> TripPlanLLMOutput:
    return TripPlanLLMOutput(
        overview=f"Lisbon is a relaxed, calm, restorative 4-day escape for 2 travelers with elegant {interest} moments.",
        best_time_to_visit="Spring",
        live_insights=[],
        attractions=[
            Attraction(
                name="Lisbon food hall",
                reason="Best for food lovers.",
                best_time="Morning",
                estimated_cost=10,
            ),
            Attraction(
                name="Riverside promenade",
                reason="Relaxed walking route.",
                best_time="Sunset",
                estimated_cost=5,
            ),
            Attraction(
                name="Design quarter",
                reason="Boutique browsing.",
                best_time="Afternoon",
                estimated_cost=8,
            ),
        ],
        itinerary=[
            DayPlan(
                day=1,
                theme="Arrival and slow orientation",
                summary="A calm, unhurried arrival with a restorative rhythm.",
                activities=[
                    Activity(
                        title="Food market wander",
                        time="10:00",
                        location="Market",
                        description="Relaxed food sampling.",
                        estimated_cost=10,
                    ),
                    Activity(
                        title="Cafe pause",
                        time="13:00",
                        location="Cafe",
                        description="Gentle local cafe break.",
                        estimated_cost=8,
                    ),
                    Activity(
                        title="Sunset walk",
                        time="18:00",
                        location="River",
                        description="Slow riverside walk.",
                        estimated_cost=0,
                    ),
                ],
                meals=["Breakfast - Hotel spread", "Lunch - Riverside cafe", "Dinner - Old town table"],
                daily_estimate=25,
            ),
            DayPlan(
                day=2,
                theme="Leisure and local texture",
                summary="Calm neighborhoods and slow observation for 2 travelers.",
                activities=[
                    Activity(
                        title="Food tasting",
                        time="10:00",
                        location="Hall",
                        description="Relaxed food exploration.",
                        estimated_cost=10,
                    ),
                    Activity(
                        title="Museum browse",
                        time="13:00",
                        location="Museum",
                        description="Gentle cultural stop.",
                        estimated_cost=12,
                    ),
                    Activity(
                        title="Evening pause",
                        time="18:00",
                        location="Lookout",
                        description="Unhurried sunset pause.",
                        estimated_cost=5,
                    ),
                ],
                meals=["Breakfast - Bakery start", "Lunch - Market plates", "Dinner - Neighborhood dining"],
                daily_estimate=27,
            ),
            DayPlan(
                day=3,
                theme=f"{mood.capitalize()} signature day",
                summary=f"A {mood} day for 2 travelers with clearly paced moments.",
                activities=[
                    Activity(
                        title="Chef lunch",
                        time="11:00",
                        location="Restaurant",
                        description="Food-led signature meal.",
                        estimated_cost=20,
                    ),
                    Activity(
                        title="Neighborhood wander",
                        time="14:00",
                        location="Quarter",
                        description="Slow browsing route.",
                        estimated_cost=5,
                    ),
                    Activity(
                        title="Twilight terrace",
                        time="19:00",
                        location="Terrace",
                        description="Calm evening terrace.",
                        estimated_cost=10,
                    ),
                ],
                meals=["Breakfast - Hotel spread", "Lunch - Chef-led tasting", "Dinner - Terrace table"],
                daily_estimate=35,
            ),
            DayPlan(
                day=4,
                theme="Reflection and departure",
                summary="A gentle wrap-up to the trip for 2 travelers.",
                activities=[
                    Activity(
                        title="Breakfast stop",
                        time="09:00",
                        location="Cafe",
                        description="Relaxed breakfast.",
                        estimated_cost=8,
                    ),
                    Activity(
                        title="Boutique browse",
                        time="11:00",
                        location="Lane",
                        description="Light shopping stroll.",
                        estimated_cost=10,
                    ),
                    Activity(
                        title="Departure transfer",
                        time="15:00",
                        location="Airport",
                        description="Calm transfer.",
                        estimated_cost=12,
                    ),
                ],
                meals=["Breakfast - Cafe stop", "Lunch - Farewell meal", "Dinner - Early airport dinner"],
                daily_estimate=30,
            ),
        ],
        cost_breakdown=CostBreakdown(
            accommodation=60,
            food=30,
            transport=20,
            activities=25,
            contingency=15,
            total=150,
        ),
        smart_suggestions=[
            SmartSuggestion(
                title="Lean into food",
                description="Keep food at the heart of the route.",
            ),
        ],
    )


def test_validate_generated_trip_accepts_strong_match() -> None:
    service = LLMService()

    issues = service._validate_generated_trip(
        build_plan(),
        "Lisbon",
        4,
        2,
        150,
        "INR",
        ["food"],
        "relaxed",
    )

    assert issues == []


def test_validate_generated_trip_rejects_missing_interest_and_bad_budget() -> None:
    service = LLMService()
    plan = build_plan()
    plan.cost_breakdown.total = 500
    plan.smart_suggestions = [
        SmartSuggestion(title="Architecture focus", description="Museums and facades.")
    ]

    issues = service._validate_generated_trip(
        plan,
        "Lisbon",
        4,
        2,
        150,
        "INR",
        ["wellness"],
        "relaxed",
    )

    assert any("Budget total" in issue for issue in issues)
    assert any("Selected interests" in issue for issue in issues)


def test_validate_generated_trip_rejects_wrong_day_count_and_missing_traveler_signal() -> (
    None
):
    service = LLMService()
    plan = build_plan()
    plan.overview = "Lisbon is a relaxed, calm city escape with elegant food moments."
    plan.itinerary = plan.itinerary[:3]
    for day in plan.itinerary:
        day.summary = day.summary.replace(" for 2 travelers", "")

    issues = service._validate_generated_trip(
        plan,
        "Lisbon",
        4,
        2,
        150,
        "INR",
        ["food"],
        "relaxed",
    )

    assert any("exactly 4 days" in issue for issue in issues)
    assert any("Traveler count" in issue for issue in issues)


def test_generate_structured_trip_with_retries_uses_groq_primary(monkeypatch) -> None:
    service = LLMService()
    service.providers = [
        {
            "label": "Groq primary",
            "kind": "groq",
            "client": None,
            "model": "openai/gpt-oss-20b",
        },
    ]
    service.retry_attempts = 3
    service.retry_backoff_seconds = 0

    memory = type(
        "MemoryStub",
        (),
        {
            "name": "",
            "travel_style": "",
            "preferred_mood": "relaxed",
            "interests": [],
            "past_trips": [],
        },
    )()
    plan = build_plan()
    attempts = {"count": 0}

    def fake_generate(*args, provider_kind: str, client, model_name: str, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError(
                "503 UNAVAILABLE. This model is currently experiencing high demand."
            )
        return plan

    monkeypatch.setattr(service, "_generate_structured_trip", fake_generate)

    result = service._generate_structured_trip_with_failover(
        "Lisbon",
        4,
        2,
        150,
        "INR",
        ["food"],
        "relaxed",
        memory,
        {},
        [],
    )

    assert result is plan
    assert attempts["count"] == 3


def test_enforce_user_constraints_repairs_destination_and_relaxed_themes() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan().model_dump())
    plan.overview = "A calm temple-town escape with food-led pauses."
    for day in plan.itinerary:
        day.theme = "Sacred circuit"
        day.meals = []

    repaired = service._enforce_user_constraints(
        plan,
        destination="Tirumala, Tirupati, Andhra Pradesh",
        mood="relaxed",
        research={
            "best_time_hint": "October to February (cooler temple-town weather and more comfortable hill visits)"
        },
    )

    assert "Tirumala, Tirupati, Andhra Pradesh" in repaired.overview
    assert all(day.theme.lower().startswith("relaxed ") for day in repaired.itinerary)
    assert all(service._has_required_meals(day.meals) for day in repaired.itinerary)
    assert all(len(day.activities) >= 3 for day in repaired.itinerary)
    assert (
        repaired.best_time_to_visit
        == "October to February (cooler temple-town weather and more comfortable hill visits)"
    )


def test_enforce_user_constraints_rewrites_placeholder_overview() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan().model_dump())
    plan.overview = (
        "Lisbon is framed as a cinematic 4-day itinerary for 2 travelers, "
        "tuned for relaxed energy, local flavor, and a realistic INR-based budget."
    )

    repaired = service._enforce_user_constraints(
        plan,
        destination="Lisbon, Portugal",
        mood="relaxed",
        research={},
        traveler_count=2,
        interests=["food", "culture"],
        days=4,
    )

    assert "This 4-day relaxed trip to Lisbon, Portugal" in repaired.overview
    assert "Day 1 focused on" in repaired.overview
    assert "Day 4 centered on" in repaired.overview
    assert "Food market wander" in repaired.overview


def test_enforce_user_constraints_repairs_short_adventure_activities() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan(mood="adventure").model_dump())
    for day in plan.itinerary:
        day.theme = "City circuit"
        day.activities = [
            Activity(
                title="Morning walk",
                time="09:00",
                location="Center",
                description="A simple start to the day.",
                estimated_cost=5,
            )
        ]

    repaired = service._enforce_user_constraints(
        plan,
        destination="Hyderabad, Telangana",
        mood="adventure",
        research={
            "best_time_hint": "October to February (cooler weather and more comfortable city days)"
        },
    )

    assert all(len(day.activities) >= 3 for day in repaired.itinerary)
    assert any(
        any(
            term in f"{activity.title} {activity.description}".lower()
            for term in {"adventure", "trail", "explore", "active", "bold"}
        )
        for day in repaired.itinerary
        for activity in day.activities
    )


def test_enforce_user_constraints_repairs_missing_itinerary_days() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan().model_dump())
    plan.itinerary = plan.itinerary[:2]
    for day in plan.itinerary:
        day.theme = "Coastal circuit"
        day.activities = []

    repaired = service._enforce_user_constraints(
        plan,
        destination="Goa, India",
        mood="relaxed",
        research={},
        traveler_count=2,
        interests=["beaches", "food"],
        days=4,
        budget=20000,
        arrival_time="11:00",
    )

    assert len(repaired.itinerary) == 4
    assert [day.day for day in repaired.itinerary] == [1, 2, 3, 4]
    assert all(len(day.activities) >= 3 for day in repaired.itinerary)
    issues = service._validate_generated_trip(
        repaired,
        "Goa, India",
        4,
        2,
        20000,
        "INR",
        ["beaches", "food"],
        "relaxed",
    )
    assert "The itinerary must include exactly 4 days." not in issues
    assert (
        "Requested mood relaxed is not reflected clearly in day themes."
        not in issues
    )


def test_fallback_itinerary_uses_dynamic_activity_counts() -> None:
    service = LLMService()

    itinerary = service._build_fallback_itinerary(
        destination="Goa, India",
        days=4,
        traveler_label="2 travelers",
        mood="relaxed",
        interest_a="beaches",
        interest_b="food",
        daily_base=5000,
        activity_cost=1400,
        arrival_time="11:00",
    )

    counts = [len(day.activities) for day in itinerary]
    assert counts == [3, 4, 4, 3]


def test_repair_day_meals_enforces_breakfast_lunch_dinner_and_snacks() -> None:
    service = LLMService()

    meals = service._repair_day_meals(
        ["Brunch at hotel cafe", "Seafood dinner by the beach"],
        2,
        "Goa, India",
        activity_count=4,
    )

    meal_text = " ".join(meals).lower()
    assert "breakfast" in meal_text
    assert "lunch" in meal_text
    assert "dinner" in meal_text
    assert "snacks" in meal_text


def test_validate_generated_trip_accepts_composite_destination_markers() -> None:
    service = LLMService()
    plan = build_plan()
    plan.overview = "Tirumala offers a relaxed temple-town escape, while Tirupati keeps the route practical."
    plan.attractions[0].name = "Tirumala hill viewpoint"
    plan.itinerary[0].activities[0].location = "Tirupati"

    issues = service._validate_generated_trip(
        plan,
        "Tirumala, Tirupati, Andhra Pradesh",
        4,
        2,
        150,
        "INR",
        ["food"],
        "relaxed",
    )

    assert not any(
        "Destination Tirumala, Tirupati, Andhra Pradesh" in issue for issue in issues
    )


def test_generate_with_groq_uses_json_object_mode_and_local_json_parsing(
    monkeypatch,
) -> None:
    service = LLMService()
    service.groq_api_key = "test-key"
    service.groq_base_url = "https://api.groq.com/openai/v1"
    captured_payload: dict[str, object] = {}

    plan = build_plan()
    content = f"```json\n{json.dumps(plan.model_dump(mode='json'))}\n```"

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": content,
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None):
            captured_payload["url"] = url
            captured_payload["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.services.llm_service.httpx.Client", FakeClient)

    result = service._generate_with_groq(
        model_name="openai/gpt-oss-20b",
        system_prompt="System prompt",
        user_prompt="User prompt",
        destination="Lisbon",
        days=4,
        budget=150,
    )

    assert result.overview == plan.overview
    assert captured_payload["json"]["response_format"] == {"type": "json_object"}


def test_generate_with_groq_retries_without_json_mode_after_provider_400(
    monkeypatch,
) -> None:
    service = LLMService()
    service.groq_api_key = "test-key"
    service.groq_base_url = "https://api.groq.com/openai/v1"
    calls: list[dict[str, object]] = []

    plan = build_plan()

    class FirstResponse:
        status_code = 400

        def json(self):
            return {
                "error": {
                    "message": "Failed to validate JSON. Please adjust your prompt. See 'failed_generation' for more details."
                }
            }

    class SecondResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(plan.model_dump(mode="json")),
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None):
            calls.append(json)
            self._calls += 1
            if self._calls == 1:
                return FirstResponse()
            return SecondResponse()

    monkeypatch.setattr("app.services.llm_service.httpx.Client", FakeClient)

    result = service._generate_with_groq(
        model_name="openai/gpt-oss-20b",
        system_prompt="System prompt",
        user_prompt="User prompt",
        destination="Lisbon",
        days=4,
        budget=150,
    )

    assert result.overview == plan.overview
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in calls[1]


def test_generate_with_groq_parses_list_content_blocks(monkeypatch) -> None:
    service = LLMService()
    service.groq_api_key = "test-key"
    service.groq_base_url = "https://api.groq.com/openai/v1"

    plan = build_plan()
    content = [
        {
            "type": "text",
            "text": json.dumps(plan.model_dump(mode="json")),
        }
    ]

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": content,
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None):
            return FakeResponse()

    monkeypatch.setattr("app.services.llm_service.httpx.Client", FakeClient)

    result = service._generate_with_groq(
        model_name="openai/gpt-oss-20b",
        system_prompt="System prompt",
        user_prompt="User prompt",
        destination="Lisbon",
        days=4,
        budget=150,
    )

    assert result.overview == plan.overview


def test_extract_json_object_ignores_trailing_extra_text() -> None:
    service = LLMService()
    plan = build_plan().model_dump(mode="json")
    content = (
        json.dumps(plan)
        + "\n\nAdditional notes:\n- keep it flexible\n- verify opening hours"
    )

    parsed = service._extract_json_object(content)

    assert parsed["overview"] == plan["overview"]
    assert parsed["itinerary"][0]["activities"][0]["title"] == plan["itinerary"][0]["activities"][0]["title"]


def test_normalize_trip_plan_payload_coerces_common_groq_shapes() -> None:
    service = LLMService()

    normalized = service._normalize_trip_plan_payload(
        {
            "overview": "Relaxed temple-town journey.",
            "best_time_to_visit": "Winter mornings",
            "live_insights": "Tirupati's food streets stay lively after darshan hours.",
            "attractions": [
                {
                    "name": "Temple entrance",
                    "reason": "Iconic spiritual arrival.",
                    "best_time": "Early morning",
                    "estimated_cost": "₹0 (entry is free but donations optional)",
                }
            ],
            "itinerary": [
                {
                    "day": 1,
                    "theme": "Arrival",
                    "summary": "Settle in gently.",
                    "activities": [
                        {
                            "title": "Temple walk",
                            "time": "08:00",
                            "location": "Tirumala",
                            "description": "A calm first circuit.",
                            "estimated_cost": "₹200",
                        }
                    ],
                    "meals": [
                        {
                            "name": "Breakfast",
                            "location": "Hotel dining",
                            "estimated_cost": "₹0",
                        },
                        {
                            "name": "Dinner",
                            "location": "Local restaurant",
                            "estimated_cost": "₹150",
                        },
                    ],
                }
            ],
            "smart_suggestions": ["Arrive before the first darshan window."],
        },
        destination="Tirumala, Tirupati, Andhra Pradesh",
        days=1,
        budget=1200,
    )

    assert normalized["live_insights"] == [
        "Tirupati's food streets stay lively after darshan hours."
    ]
    assert normalized["attractions"][0]["estimated_cost"] == 0.0
    assert normalized["itinerary"][0]["activities"][0]["estimated_cost"] == 200.0
    assert normalized["itinerary"][0]["meals"][0] == "Breakfast - Hotel dining"
    assert normalized["itinerary"][0]["daily_estimate"] == 200.0
    assert normalized["cost_breakdown"]["total"] == 1200.0


def test_normalize_activities_accepts_common_alternate_shapes() -> None:
    service = LLMService()

    activities = service._normalize_activities(
        [
            {
                "name": "Baga beach walk",
                "start_time": "08:00",
                "place": "Baga Beach",
                "notes": "Start with a calm shoreline walk.",
                "cost": "₹0",
            },
            "Sunset shacks and live music",
        ]
    )

    assert activities[0]["title"] == "Baga beach walk"
    assert activities[0]["time"] == "08:00"
    assert activities[0]["location"] == "Baga Beach"
    assert activities[0]["description"] == "Start with a calm shoreline walk."
    assert activities[1]["title"] == "Sunset shacks and live music"


def test_normalize_local_places_accepts_common_alternate_shapes() -> None:
    service = LLMService()

    places = service._normalize_local_places(
        [
            {
                "title": "Gunpowder",
                "location": "Assagao",
                "category": "restaurant",
                "recommended_time": "Lunch",
                "description": "A relaxed Goan lunch stop in a lush courtyard.",
                "entry_fee": "₹800",
            }
        ]
    )

    assert places[0]["name"] == "Gunpowder"
    assert places[0]["area"] == "Assagao"
    assert places[0]["place_type"] == "restaurant"
    assert places[0]["best_time"] == "Lunch"
    assert places[0]["why_go"] == "A relaxed Goan lunch stop in a lush courtyard."
    assert places[0]["estimated_cost"] == 800.0


def test_normalize_cost_breakdown_accepts_alternate_keys_and_fills_missing_values() -> None:
    service = LLMService()

    result = service._normalize_cost_breakdown(
        {
            "hotel_cost": "₹7000",
            "food_budget": "₹3500",
            "transportation": "₹1800",
            "experience_cost": "₹2400",
            "total": "₹20000",
        },
        itinerary=[],
        attractions=[],
        budget=20000,
    )

    assert result["accommodation"] == 7000.0
    assert result["food"] == 3500.0
    assert result["transport"] == 1800.0
    assert result["activities"] > 0
    assert result["contingency"] >= 0
    assert result["total"] == 20000.0


def test_enforce_user_constraints_replaces_placeholder_activity_content() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan().model_dump())
    for day in plan.itinerary:
        day.activities = [
            Activity(
                title="Planned activity",
                time="Flexible",
                location="Destination",
                description="A relevant stop for the trip.",
                estimated_cost=0,
            )
        ]

    repaired = service._enforce_user_constraints(
        plan,
        destination="Goa, India",
        mood="relaxed",
        research={},
        traveler_count=2,
        interests=["beaches", "food"],
        days=4,
        budget=20000,
        arrival_time="11:00",
    )

    assert repaired.itinerary[0].activities[0].title != "Planned activity"
    assert repaired.itinerary[0].activities[0].location != "Destination"
    assert "Goa, India" not in {
        activity.title for day in repaired.itinerary for activity in day.activities
    }


def test_enforce_user_constraints_upgrades_generic_activity_copy() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan().model_dump())
    plan.itinerary[1].activities = [
        Activity(
            title="Day 2 stop 4",
            time="15:30",
            location="Destination",
            description="A relevant stop for the trip.",
            estimated_cost=0,
        )
    ]

    repaired = service._enforce_user_constraints(
        plan,
        destination="Goa, India",
        mood="relaxed",
        research={},
        traveler_count=2,
        interests=["beaches", "food"],
        days=4,
        budget=20000,
        arrival_time="11:00",
    )

    activity = repaired.itinerary[1].activities[0]
    assert "Day 2 stop 4" != activity.title
    assert activity.location != "Destination"
    assert "A relevant stop for the trip." != activity.description
    assert len(repaired.itinerary[1].activities) >= 3


def test_enforce_user_constraints_weaves_local_places_and_attractions_into_itinerary() -> None:
    service = LLMService()
    plan = TripPlanLLMOutput.model_validate(build_plan().model_dump())
    plan.hotel_recommendations = [
        HotelRecommendation(
            name="Coral Bay Stay",
            area="Beach Road",
            category="boutique hotel",
            nightly_estimate=4500,
            why_it_fits="Keeps the trip close to the waterfront and local cafes.",
            booking_tip="Book sea-facing rooms early.",
        )
    ]
    plan.local_places = [
        LocalPlace(
            name="Sundown Cafe",
            area="Harbor Front",
            place_type="cafe",
            best_time="Evening",
            why_go="Good for coffee and an easy waterfront pause.",
            estimated_cost=350,
        )
    ]
    plan.attractions = [
        Attraction(
            name="Pulicat Lake Viewpoint",
            reason="Best open-water stop for the route.",
            best_time="Sunset",
            estimated_cost=200,
        ),
        *plan.attractions[1:],
    ]
    for day in plan.itinerary:
        day.activities = [
            Activity(
                title="Planned activity",
                time="10:00",
                location="Destination",
                description="A relevant stop for the trip.",
                estimated_cost=0,
            ),
            Activity(
                title="Planned activity",
                time="14:00",
                location="Destination",
                description="A relevant stop for the trip.",
                estimated_cost=0,
            ),
            Activity(
                title="Planned activity",
                time="18:00",
                location="Destination",
                description="A relevant stop for the trip.",
                estimated_cost=0,
            ),
        ]

    repaired = service._enforce_user_constraints(
        plan,
        destination="Nellore, Andhra Pradesh",
        mood="relaxed",
        research={},
        traveler_count=2,
        interests=["food", "nature"],
        days=4,
        budget=20000,
        arrival_time="10:00",
    )

    activity_text = " ".join(
        " ".join([activity.title, activity.location, activity.description])
        for day in repaired.itinerary
        for activity in day.activities
    )
    assert "Coral Bay Stay" in activity_text
    assert "Sundown Cafe" in activity_text
    assert "Pulicat Lake Viewpoint" in activity_text
