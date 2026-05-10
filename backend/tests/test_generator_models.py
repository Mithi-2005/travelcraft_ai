from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import GenerateTripRequest


def test_generate_trip_request_accepts_positive_budget_and_inr_currency() -> None:
    payload = GenerateTripRequest(
        destination=" Tokyo ",
        days=5,
        traveler_count=3,
        budget=150,
        currency_code="INR",
        interests=[" food ", "art"],
        mood="relaxed",
    )

    assert payload.destination == "Tokyo"
    assert payload.days == 5
    assert payload.traveler_count == 3
    assert payload.budget == 150
    assert payload.currency_code == "INR"
    assert payload.interests == ["food", "art"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("destination", "   "),
        ("days", 0),
        ("traveler_count", 0),
        ("budget", 0),
        ("budget", -1),
        ("interests", []),
        ("currency_code", "JPY"),
    ],
)
def test_generate_trip_request_rejects_invalid_inputs(field: str, value: object) -> None:
    payload = {
        "destination": "Lisbon",
        "days": 4,
        "traveler_count": 2,
        "budget": 500,
        "currency_code": "INR",
        "interests": ["food"],
        "mood": "relaxed",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        GenerateTripRequest(**payload)
