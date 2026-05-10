from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.security import get_current_user


@contextmanager
def override_dependencies():
    app.dependency_overrides[get_current_user] = lambda: type("UserObj", (), {"id": "user-1", "name": "Test"})()
    app.dependency_overrides[get_db] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def test_generate_trip_route_returns_currency_code(monkeypatch) -> None:
    async def fake_generate_trip(payload, memory):
        return {
            "trip_id": "trip-123",
            "destination": payload.destination,
            "days": payload.days,
            "traveler_count": payload.traveler_count,
            "budget": payload.budget,
            "currency_code": payload.currency_code,
            "interests": payload.interests,
            "mood": payload.mood,
            "generated_at": "2026-01-01T00:00:00+00:00",
            "overview": "Overview",
            "best_time_to_visit": "Spring",
            "live_insights": [],
            "attractions": [],
            "itinerary": [],
            "cost_breakdown": {
                "accommodation": 10,
                "food": 10,
                "transport": 10,
                "activities": 10,
                "contingency": 10,
                "total": payload.budget,
            },
            "smart_suggestions": [],
            "research_mode": "fallback",
            "research_error": None,
            "research_sources": [],
            "llm_mode": "fallback",
            "llm_error": None,
        }

    monkeypatch.setattr("app.main.memory_service.load_memory", lambda db, user: {})
    monkeypatch.setattr("app.main.memory_service.store_generated_trip", lambda db, user, payload, plan: None)
    monkeypatch.setattr("app.main.planner_service.generate_trip", fake_generate_trip)

    with override_dependencies():
        client = TestClient(app)
        response = client.post(
            "/generate-trip",
            json={
                "destination": "Tokyo",
                "days": 5,
                "traveler_count": 3,
                "budget": 150,
                "currency_code": "INR",
                "interests": ["food"],
                "mood": "relaxed",
            },
        )

    assert response.status_code == 200
    assert response.json()["currency_code"] == "INR"
    assert response.json()["days"] == 5
    assert response.json()["traveler_count"] == 3


def test_generate_trip_route_rejects_invalid_payload(monkeypatch) -> None:
    monkeypatch.setattr("app.main.memory_service.load_memory", lambda db, user: {})

    with override_dependencies():
        client = TestClient(app)
        response = client.post(
            "/generate-trip",
            json={
                "destination": "Tokyo",
                "days": 0,
                "traveler_count": 0,
                "budget": 0,
                "currency_code": "INR",
                "interests": [],
                "mood": "relaxed",
            },
        )

    assert response.status_code == 422


def test_get_trip_route_returns_saved_trip(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.memory_service.get_trip",
        lambda db, user, trip_id: {
            "trip_id": trip_id,
            "destination": "Tokyo",
            "days": 5,
            "traveler_count": 2,
            "budget": 22000,
            "currency_code": "INR",
            "interests": ["food"],
            "mood": "relaxed",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "overview": "Overview",
            "best_time_to_visit": "March to May",
            "live_insights": [],
            "attractions": [],
            "itinerary": [],
            "cost_breakdown": {
                "accommodation": 10,
                "food": 10,
                "transport": 10,
                "activities": 10,
                "contingency": 10,
                "total": 22000,
            },
            "smart_suggestions": [],
            "research_mode": "live",
            "research_error": None,
            "research_sources": [],
            "llm_mode": "live",
            "llm_error": None,
            "highlight": "Tokyo food hall",
        },
    )

    with override_dependencies():
        client = TestClient(app)
        response = client.get("/trips/trip-123")

    assert response.status_code == 200
    assert response.json()["trip_id"] == "trip-123"
    assert response.json()["destination"] == "Tokyo"


def test_get_trip_route_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.main.memory_service.get_trip", lambda db, user, trip_id: None)

    with override_dependencies():
        client = TestClient(app)
        response = client.get("/trips/missing-trip")

    assert response.status_code == 404


def test_destination_suggestions_route_returns_detailed_matches(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        "app.main.destination_service.search",
        lambda q, limit=6: [
        {
            "id": "lisbon-portugal",
            "name": "Lisbon",
            "country": "Portugal",
            "region": "Lisbon District",
            "display_name": "Lisbon, Portugal",
            "description": "Sunlit hill city with tram-lined streets and riverside sunsets.",
            "highlights": ["architecture", "food", "walking city"],
        }
        ],
    )
    response = client.get("/destination-suggestions", params={"q": "lis"})

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["display_name"] == "Lisbon, Portugal"
    assert payload[0]["country"] == "Portugal"
    assert payload[0]["description"]
    assert payload[0]["highlights"]

def test_destination_suggestions_route_returns_empty_for_short_queries(monkeypatch) -> None:
    monkeypatch.setattr("app.main.destination_service.search", lambda q, limit=6: [])
    client = TestClient(app)
    response = client.get("/destination-suggestions", params={"q": "l"})

    assert response.status_code == 200
    assert response.json() == []
