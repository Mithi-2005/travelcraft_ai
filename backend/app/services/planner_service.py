from __future__ import annotations

from app.models import GenerateTripRequest, TripPlanResponse, UserMemory
from app.services.firecrawl_service import FirecrawlService
from app.services.llm_service import LLMService


class PlannerService:
    def __init__(self) -> None:
        self.firecrawl = FirecrawlService()
        self.llm = LLMService()

    async def generate_trip(self, request: GenerateTripRequest, memory: UserMemory) -> TripPlanResponse:
        research = await self.firecrawl.research_destination(
            request.destination,
            request.interests,
            request.mood,
            request.days,
            request.traveler_count,
            request.budget,
            request.currency_code,
        )
        result = await self.llm.generate_trip(
            request.destination,
            request.days,
            request.arrival_time,
            request.traveler_count,
            request.budget,
            request.currency_code,
            request.interests,
            request.mood,
            memory,
            research,
            pace=request.pace,
            accommodation_style=request.accommodation_style,
            food_preference=request.food_preference,
            must_include=request.must_include,
            avoid=request.avoid,
        )
        return TripPlanResponse(
            **result.model_dump(),
            destination=request.destination,
            days=request.days,
            traveler_count=request.traveler_count,
            budget=request.budget,
            currency_code=request.currency_code,
            interests=request.interests,
            mood=request.mood,
        )
