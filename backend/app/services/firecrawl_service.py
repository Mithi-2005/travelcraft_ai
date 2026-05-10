from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import urlparse

from app.config import settings

try:
    from firecrawl import FirecrawlApp, ScrapeOptions
except Exception:  # pragma: no cover - optional dependency during static review
    FirecrawlApp = None
    ScrapeOptions = None


logger = logging.getLogger(__name__)
MONTH_RANGE_PATTERN = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b"
    r"\s*(?:to|through|until|-|–)\s*"
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)


class FirecrawlService:
    def __init__(self) -> None:
        self.client = (
            FirecrawlApp(api_key=settings.firecrawl_api_key)
            if settings.firecrawl_api_key and FirecrawlApp
            else None
        )

    async def research_destination(
        self,
        destination: str,
        interests: list[str],
        mood: str,
        days: int,
        traveler_count: int,
        budget: float,
        currency_code: str,
    ) -> dict[str, Any]:
        if not self.client:
            reason = "Firecrawl client unavailable. Check FIRECRAWL_API_KEY and installed dependency."
            logger.warning(reason)
            return self._fallback(destination, interests, mood, days, traveler_count, budget, currency_code, reason)

        try:
            return await asyncio.to_thread(
                self._run_search, destination, interests, mood, days, traveler_count, budget, currency_code
            )
        except Exception as exc:
            logger.exception("Firecrawl research failed for %s", destination)
            return self._fallback(destination, interests, mood, days, traveler_count, budget, currency_code, str(exc))

    def _run_search(
        self,
        destination: str,
        interests: list[str],
        mood: str,
        days: int,
        traveler_count: int,
        budget: float,
        currency_code: str,
    ) -> dict[str, Any]:
        budget_tier = self._budget_tier(budget)
        interest_focus = ", ".join(interests[:4]) or "authentic experiences"
        local_currency_hint = self._local_currency_hint(destination, currency_code)
        traveler_phrase = self._traveler_phrase(traveler_count)
        query = (
            f"{destination} travel guide for a {days}-day {mood} trip for {traveler_phrase}. "
            f"Prioritize {interest_focus}. "
            f"Budget tier: {budget_tier} with target full-trip spend around {budget:.0f} {currency_code} for the entire group. "
            "Weight current local neighborhoods, signature attractions, transit convenience, food, and realistic costs. "
            f"Prefer sources that clearly match the requested mood, day count, traveler count, and interests. {local_currency_hint}"
        )
        response = self.client.search(
            query,
            limit=4,
            scrape_options=ScrapeOptions(
                formats=["markdown"],
                onlyMainContent=True,
            ) if ScrapeOptions else None,
        )
        raw_items = []
        if hasattr(response, "data"):
            raw_items = response.data or []
        elif isinstance(response, dict):
            raw_items = response.get("data", [])

        insights: list[str] = []
        sources: list[dict[str, str]] = []
        for item in raw_items[:4]:
            payload = self._coerce_item(item)
            markdown = self._clean_text(payload.get("markdown") or "")
            description = self._clean_text(payload.get("description") or "")
            title = payload.get("title") or payload.get("url") or "Untitled source"
            url = payload.get("url", "")
            snippet = self._build_snippet(description, markdown)
            if snippet:
                insights.append(f"{title}: {snippet}")
            sources.append(
                {
                    "title": title,
                    "url": url,
                    "domain": self._extract_domain(url),
                    "snippet": snippet,
                }
            )

        if not insights:
            return self._fallback(
                destination,
                interests,
                mood,
                days,
                traveler_count,
                budget,
                currency_code,
                "No useful live research results returned.",
            )

        best_time_hint = self._infer_best_time(destination, insights)

        return {
            "summary": insights,
            "sources": sources,
            "mode": "live",
            "error": None,
            "best_time_hint": best_time_hint,
            "currency_code": currency_code,
            "local_currency_hint": local_currency_hint,
            "days": days,
            "traveler_count": traveler_count,
        }

    def _fallback(
        self,
        destination: str,
        interests: list[str],
        mood: str,
        days: int,
        traveler_count: int,
        budget: float,
        currency_code: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        interest_text = ", ".join(interests[:3]) or "culture and food"
        local_currency_hint = self._local_currency_hint(destination, currency_code)
        traveler_phrase = self._traveler_phrase(traveler_count)
        best_time_hint = self._infer_best_time(destination, [])
        return {
            "summary": [
                f"{destination} works well for a {days}-day {mood} itinerary for {traveler_phrase}, with room for {interest_text}.",
                f"Target full-trip spend of about {budget:.0f} {currency_code} for the group suggests a balanced mix of signature experiences and local favorites.",
                f"Focus on one anchor neighborhood per day, reserve sunset viewpoints early, and keep logistics practical for {traveler_phrase}. {local_currency_hint}",
            ],
            "sources": [],
            "mode": "fallback",
            "error": error,
            "best_time_hint": best_time_hint,
            "currency_code": currency_code,
            "local_currency_hint": local_currency_hint,
            "days": days,
            "traveler_count": traveler_count,
        }

    def _coerce_item(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if hasattr(item, "dict"):
            return item.dict()
        return {
            "title": getattr(item, "title", None),
            "description": getattr(item, "description", None),
            "markdown": getattr(item, "markdown", None),
            "url": getattr(item, "url", None),
        }

    def _build_snippet(self, description: str, markdown: str) -> str:
        primary = description or markdown
        if not primary:
            return ""
        cleaned = self._clean_text(primary)
        if len(cleaned) <= 180:
            return cleaned
        return f"{cleaned[:177].rstrip()}..."

    def _clean_text(self, value: str) -> str:
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", value)
        text = re.sub(r"\[[^\]]+\]\(([^)]+)\)", "", text)
        text = re.sub(r"#+\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_domain(self, url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def _budget_tier(self, budget: float) -> str:
        if budget < 15000:
            return "budget-conscious"
        if budget < 50000:
            return "balanced"
        if budget < 120000:
            return "premium"
        return "luxury"

    def _local_currency_hint(self, destination: str, currency_code: str) -> str:
        destination_lower = destination.lower()
        if "tokyo" in destination_lower or "japan" in destination_lower:
            local_currency = "JPY"
        elif "lisbon" in destination_lower or "paris" in destination_lower or "rome" in destination_lower or "europe" in destination_lower:
            local_currency = "EUR"
        elif "london" in destination_lower or "uk" in destination_lower:
            local_currency = "GBP"
        elif "dubai" in destination_lower or "abu dhabi" in destination_lower or "uae" in destination_lower:
            local_currency = "AED"
        elif "mumbai" in destination_lower or "delhi" in destination_lower or "india" in destination_lower:
            local_currency = "INR"
        elif "sydney" in destination_lower or "melbourne" in destination_lower or "australia" in destination_lower:
            local_currency = "AUD"
        elif "toronto" in destination_lower or "vancouver" in destination_lower or "canada" in destination_lower:
            local_currency = "CAD"
        elif "singapore" in destination_lower:
            local_currency = "SGD"
        elif "zurich" in destination_lower or "switzerland" in destination_lower:
            local_currency = "CHF"
        else:
            local_currency = currency_code

        if local_currency == currency_code:
            return f"Use realistic local prices and describe estimates directly in {currency_code}."
        return (
            f"Use realistic local prices in {local_currency} and translate them into practical traveler-facing guidance in {currency_code}."
        )

    def _traveler_phrase(self, traveler_count: int) -> str:
        return "1 traveler" if traveler_count == 1 else f"{traveler_count} travelers"

    def _infer_best_time(self, destination: str, insights: list[str]) -> str:
        combined = " ".join(insights)
        month_match = MONTH_RANGE_PATTERN.search(combined)
        if month_match:
            month_start = month_match.group(1).title()
            month_end = month_match.group(2).title()
            return f"{month_start} to {month_end} (based on current destination travel guidance)"

        destination_lower = destination.lower()
        if any(token in destination_lower for token in ("tirumala", "tirupati", "andhra pradesh")):
            return "October to February (cooler temple-town weather and more comfortable hill visits)"
        if any(token in destination_lower for token in ("goa", "kovalam", "pondicherry", "puducherry")):
            return "November to February (dry coastal weather and easier beach-to-town exploring)"
        if any(token in destination_lower for token in ("kerala", "kochi", "munnar", "alleppey")):
            return "September to March (lush scenery with gentler humidity for longer days out)"
        if any(token in destination_lower for token in ("tokyo", "kyoto", "osaka", "japan")):
            return "March to May and October to November (mild weather and strong seasonal city highlights)"
        if any(token in destination_lower for token in ("lisbon", "porto", "portugal")):
            return "April to June and September to October (warm light, easier walking weather, and fewer crowds)"
        if any(token in destination_lower for token in ("paris", "rome", "barcelona", "europe")):
            return "April to June and September to October (pleasant sightseeing weather and lighter crowd pressure)"
        if any(token in destination_lower for token in ("london", "edinburgh", "uk", "united kingdom")):
            return "May to September (longer daylight and the most reliable walking weather)"
        if any(token in destination_lower for token in ("dubai", "abu dhabi", "uae")):
            return "November to March (comfortable daytime temperatures for outdoor sightseeing)"
        if any(token in destination_lower for token in ("delhi", "agra", "jaipur", "rajasthan")):
            return "October to March (cooler northern weather and better daytime comfort)"
        if any(token in destination_lower for token in ("shimla", "manali", "leh", "kashmir", "himalaya")):
            return "April to June and September to November (clearer mountain conditions and easier road access)"
        if any(token in destination_lower for token in ("sydney", "melbourne", "australia")):
            return "September to November and March to May (mild shoulder-season weather and easier city exploring)"
        if any(token in destination_lower for token in ("singapore",)):
            return "February to April (slightly drier weather and easier daytime exploring)"
        if any(token in destination_lower for token in ("switzerland", "zurich", "lucerne", "interlaken")):
            return "June to September for alpine scenery, or December to March for winter mountain trips"
        if any(token in destination_lower for token in ("mumbai", "bengaluru", "bangalore", "hyderabad", "india")):
            return "October to February (cooler weather and more comfortable city days)"
        return "Aim for the destination's mild or dry season for the smoothest overall trip experience"
