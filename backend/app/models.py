from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator


TripMood = Literal["relaxed", "adventure", "luxury"]
ServiceMode = Literal["live", "fallback", "disabled"]
CurrencyCode = Literal["INR"]


class AuthUserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class DestinationSuggestion(BaseModel):
    id: str
    name: str
    country: str
    region: str = ""
    display_name: str
    description: str
    highlights: list[str] = Field(default_factory=list)


class Attraction(BaseModel):
    name: str
    reason: str
    best_time: str
    estimated_cost: float


class Activity(BaseModel):
    title: str
    time: str
    location: str
    description: str
    estimated_cost: float


class HotelRecommendation(BaseModel):
    name: str
    area: str
    category: str
    nightly_estimate: float
    why_it_fits: str
    booking_tip: str = ""


class LocalPlace(BaseModel):
    name: str
    area: str
    place_type: str
    best_time: str
    why_go: str
    estimated_cost: float = 0


class LogisticsPlan(BaseModel):
    arrival_transfer: str = ""
    local_transport: str = ""
    neighborhood_base: str = ""
    booking_priorities: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    packing_notes: list[str] = Field(default_factory=list)


class CustomizationSummary(BaseModel):
    pace: str = "balanced"
    accommodation_style: str = "mixed"
    food_preference: str = "local favorites"
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class DayPlan(BaseModel):
    day: int
    theme: str
    summary: str
    activities: list[Activity] = Field(default_factory=list)
    meals: list[str] = Field(default_factory=list)
    daily_estimate: float


class CostBreakdown(BaseModel):
    accommodation: float
    food: float
    transport: float
    activities: float
    contingency: float
    total: float


class SmartSuggestion(BaseModel):
    title: str
    description: str


class ResearchSource(BaseModel):
    title: str
    url: str
    domain: str = ""
    snippet: str = ""


class TripPlanLLMOutput(BaseModel):
    overview: str
    best_time_to_visit: str
    live_insights: list[str] = Field(default_factory=list)
    customization: CustomizationSummary = Field(default_factory=CustomizationSummary)
    hotel_recommendations: list[HotelRecommendation] = Field(default_factory=list)
    local_places: list[LocalPlace] = Field(default_factory=list)
    logistics: LogisticsPlan = Field(default_factory=LogisticsPlan)
    attractions: list[Attraction] = Field(default_factory=list)
    itinerary: list[DayPlan] = Field(default_factory=list)
    cost_breakdown: CostBreakdown
    smart_suggestions: list[SmartSuggestion] = Field(default_factory=list)
    research_mode: ServiceMode = "fallback"
    research_error: str | None = None
    research_sources: list[ResearchSource] = Field(default_factory=list)
    llm_mode: ServiceMode = "fallback"
    llm_error: str | None = None


class TripPlanResponse(TripPlanLLMOutput):
    trip_id: str = Field(default_factory=lambda: f"trip-{uuid4().hex[:10]}")
    destination: str
    days: int = Field(ge=1, le=30)
    traveler_count: int = Field(ge=1, le=20)
    budget: float
    currency_code: CurrencyCode = "INR"
    interests: list[str]
    mood: TripMood
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PastTrip(TripPlanResponse):
    highlight: str


class UserMemory(BaseModel):
    name: str = ""
    bio: str = ""
    home_airport: str = ""
    budget_preference: float | None = None
    travel_style: str = ""
    interests: list[str] = Field(default_factory=list)
    preferred_mood: TripMood = "relaxed"
    past_trips: list[PastTrip] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class GenerateTripRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=255)
    days: int = Field(default=4, ge=1, le=30)
    arrival_time: str = Field(default="10:00", max_length=20)
    traveler_count: int = Field(default=1, ge=1, le=20)
    budget: float = Field(gt=0)
    currency_code: CurrencyCode = "INR"
    interests: list[str] = Field(default_factory=list, min_length=1)
    mood: TripMood = "relaxed"
    pace: str = Field(default="balanced", max_length=40)
    accommodation_style: str = Field(default="mixed", max_length=60)
    food_preference: str = Field(default="local favorites", max_length=120)
    must_include: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Destination is required.")
        return normalized

    @field_validator("interests", mode="before")
    @classmethod
    def normalize_interests(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        normalized = []
        for item in value:
            cleaned = str(item).strip()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Select at least one interest.")
        return value

    @field_validator("must_include", "avoid", mode="before")
    @classmethod
    def normalize_optional_lists(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",")
        return [str(item).strip() for item in value if str(item).strip()]


class UpdateMemoryRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
    home_airport: str | None = None
    budget_preference: float | None = None
    travel_style: str | None = None
    interests: list[str] | None = None
    preferred_mood: TripMood | None = None
