from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.models import DestinationSuggestion


@dataclass(frozen=True)
class DestinationRecord:
    id: str
    name: str
    country: str
    region: str
    description: str
    highlights: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    popularity: int = 0

    @property
    def display_name(self) -> str:
        return f"{self.name}, {self.country}"


DESTINATION_CATALOG: tuple[DestinationRecord, ...] = (
    DestinationRecord(
        id="mumbai-india",
        name="Mumbai",
        country="India",
        region="Maharashtra",
        description="Fast-paced coastal city with luxury hotels, iconic food neighborhoods, sea views, and high-energy culture.",
        highlights=("street food", "art deco", "luxury stays"),
        aliases=("bombay",),
        popularity=100,
    ),
    DestinationRecord(
        id="goa-india",
        name="Goa",
        country="India",
        region="Konkan Coast",
        description="Beach-forward escape with Portuguese heritage, sunset shacks, boutique stays, and relaxed coastal pacing.",
        highlights=("beaches", "nightlife", "slow travel"),
        popularity=98,
    ),
    DestinationRecord(
        id="jaipur-india",
        name="Jaipur",
        country="India",
        region="Rajasthan",
        description="Palace city known for heritage hotels, craft markets, bold architecture, and colorful cultural experiences.",
        highlights=("heritage", "shopping", "architecture"),
        popularity=96,
    ),
    DestinationRecord(
        id="udaipur-india",
        name="Udaipur",
        country="India",
        region="Rajasthan",
        description="Romantic lake city with palace views, rooftop dining, serene boat rides, and elegant old-world texture.",
        highlights=("lakes", "romantic", "luxury"),
        popularity=92,
    ),
    DestinationRecord(
        id="new-delhi-india",
        name="New Delhi",
        country="India",
        region="National Capital Region",
        description="Layered capital city with monuments, modern restaurants, museums, and broad choices from culture to nightlife.",
        highlights=("culture", "history", "food"),
        aliases=("delhi",),
        popularity=95,
    ),
    DestinationRecord(
        id="bengaluru-india",
        name="Bengaluru",
        country="India",
        region="Karnataka",
        description="Garden city with specialty coffee, startup energy, modern dining, and nearby nature breaks.",
        highlights=("cafes", "nightlife", "city breaks"),
        aliases=("bangalore",),
        popularity=89,
    ),
    DestinationRecord(
        id="kochi-india",
        name="Kochi",
        country="India",
        region="Kerala",
        description="Historic port city with spice routes, waterside calm, art spaces, and easy access to slower Kerala itineraries.",
        highlights=("heritage", "art", "waterfront"),
        aliases=("cochin",),
        popularity=84,
    ),
    DestinationRecord(
        id="manali-india",
        name="Manali",
        country="India",
        region="Himachal Pradesh",
        description="Mountain retreat with alpine views, adventure access, cool-weather cafes, and scenic road-trip energy.",
        highlights=("mountains", "adventure", "nature"),
        popularity=82,
    ),
    DestinationRecord(
        id="tokyo-japan",
        name="Tokyo",
        country="Japan",
        region="Kanto",
        description="High-design megacity with Michelin dining, precision transit, hidden alleys, and constantly shifting neighborhoods.",
        highlights=("food", "design", "nightlife"),
        popularity=97,
    ),
    DestinationRecord(
        id="kyoto-japan",
        name="Kyoto",
        country="Japan",
        region="Kansai",
        description="Temple-rich cultural city with seasonal beauty, traditional tea houses, thoughtful pacing, and refined craft.",
        highlights=("culture", "temples", "slow travel"),
        popularity=91,
    ),
    DestinationRecord(
        id="bangkok-thailand",
        name="Bangkok",
        country="Thailand",
        region="Central Thailand",
        description="Electric city of temples, rooftop bars, riverfront hotels, and layered food culture across every budget level.",
        highlights=("street food", "luxury", "nightlife"),
        popularity=93,
    ),
    DestinationRecord(
        id="bali-indonesia",
        name="Bali",
        country="Indonesia",
        region="Lesser Sunda Islands",
        description="Villa-heavy island destination with wellness retreats, surf towns, rice terraces, and relaxed tropical flow.",
        highlights=("wellness", "beaches", "nature"),
        popularity=94,
    ),
    DestinationRecord(
        id="dubai-uae",
        name="Dubai",
        country="United Arab Emirates",
        region="Dubai",
        description="High-gloss destination known for elevated hospitality, desert experiences, major shopping, and skyline dining.",
        highlights=("luxury", "shopping", "desert"),
        popularity=92,
    ),
    DestinationRecord(
        id="lisbon-portugal",
        name="Lisbon",
        country="Portugal",
        region="Lisbon District",
        description="Sunlit hill city with tram-lined streets, tiled facades, riverside sunsets, and excellent value for culture lovers.",
        highlights=("architecture", "food", "walking city"),
        popularity=95,
    ),
    DestinationRecord(
        id="paris-france",
        name="Paris",
        country="France",
        region="Ile-de-France",
        description="Classic capital for art, cafes, luxury shopping, and elegant neighborhood wandering with strong museum density.",
        highlights=("art", "cafes", "luxury"),
        popularity=96,
    ),
    DestinationRecord(
        id="rome-italy",
        name="Rome",
        country="Italy",
        region="Lazio",
        description="Layered historic city with iconic ruins, atmospheric piazzas, late dinners, and rich neighborhood texture.",
        highlights=("history", "food", "architecture"),
        popularity=94,
    ),
    DestinationRecord(
        id="barcelona-spain",
        name="Barcelona",
        country="Spain",
        region="Catalonia",
        description="Creative coastal city with Gaudi landmarks, beach access, strong nightlife, and excellent urban energy.",
        highlights=("architecture", "beach", "nightlife"),
        popularity=93,
    ),
    DestinationRecord(
        id="london-uk",
        name="London",
        country="United Kingdom",
        region="England",
        description="Global city with museums, theater, design hotels, neighborhood markets, and strong premium travel options.",
        highlights=("culture", "shopping", "theater"),
        popularity=95,
    ),
    DestinationRecord(
        id="new-york-usa",
        name="New York City",
        country="United States",
        region="New York",
        description="Fast-moving cultural capital with neighborhoods, theater, skyline dining, and dense premium city experiences.",
        highlights=("city breaks", "food", "arts"),
        aliases=("new york", "nyc"),
        popularity=94,
    ),
)


class DestinationService:
    def __init__(self) -> None:
        self.google_places_api_key = settings.google_places_api_key
        self.google_places_url = settings.google_places_autocomplete_url
        self.google_places_region_code = settings.google_places_region_code
        self.google_places_language_code = settings.google_places_language_code
        self.google_places_field_mask = settings.google_places_field_mask
        self.timeout_seconds = settings.destination_suggestions_timeout_seconds

    def search(self, query: str, limit: int = 6) -> list[DestinationSuggestion]:
        normalized_query = self._normalize(query)
        if len(normalized_query) < 2:
            return []

        limit = max(1, min(limit, 8))

        try:
            external_results = self._search_external(normalized_query, limit)
            if external_results:
                return external_results
        except Exception:
            pass

        return self._search_catalog(normalized_query, limit)

    def _search_external(self, query: str, limit: int) -> list[DestinationSuggestion]:
        if not self.google_places_api_key:
            return []
        return self._search_google_places(query, limit)

    def _search_google_places(self, query: str, limit: int) -> list[DestinationSuggestion]:
        payload = {
            "input": query,
            "inputOffset": len(query),
            "languageCode": self.google_places_language_code,
            "regionCode": self.google_places_region_code,
            "includeQueryPredictions": False,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.google_places_api_key,
            "X-Goog-FieldMask": self.google_places_field_mask,
        }

        with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
            response = client.post(self.google_places_url, json=payload)
            response.raise_for_status()

        payload = response.json()
        results = payload.get("suggestions", []) if isinstance(payload, dict) else []
        suggestions: list[DestinationSuggestion] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            place_prediction = item.get("placePrediction")
            if not isinstance(place_prediction, dict):
                continue
            suggestions.append(self._serialize_google_place(place_prediction))
        return self._apply_country_bias(self._dedupe_suggestions(suggestions, limit), query, limit)

    def _search_catalog(self, query: str, limit: int) -> list[DestinationSuggestion]:
        ranked: list[tuple[int, DestinationRecord]] = []
        for record in DESTINATION_CATALOG:
            score = self._score(record, query)
            if score > 0:
                ranked.append((score, record))

        ranked.sort(key=lambda item: (item[0], item[1].popularity, item[1].name), reverse=True)
        suggestions = [self._serialize_record(record) for _, record in ranked[:limit]]
        return self._apply_country_bias(suggestions, query, limit)

    def _serialize_google_place(self, item: dict[str, Any]) -> DestinationSuggestion:
        text_payload = item.get("text") if isinstance(item.get("text"), dict) else {}
        structured = item.get("structuredFormat") if isinstance(item.get("structuredFormat"), dict) else {}
        main_text_payload = structured.get("mainText") if isinstance(structured.get("mainText"), dict) else {}
        secondary_text_payload = (
            structured.get("secondaryText") if isinstance(structured.get("secondaryText"), dict) else {}
        )

        full_text = str(text_payload.get("text") or "").strip()
        name = str(main_text_payload.get("text") or full_text.split(",")[0] or "").strip()
        secondary_text = str(secondary_text_payload.get("text") or "").strip()
        if not secondary_text and "," in full_text:
            secondary_text = ",".join(part.strip() for part in full_text.split(",")[1:] if part.strip())

        secondary_segments = [segment.strip() for segment in secondary_text.split(",") if segment.strip()]
        country = secondary_segments[-1] if secondary_segments else ""
        region = secondary_segments[0] if secondary_segments else ""
        display_name = full_text or ", ".join(part for part in (name, secondary_text) if part)

        raw_types = item.get("types") if isinstance(item.get("types"), list) else []
        highlights = self._build_google_highlights(raw_types, region, country)
        description = self._build_google_description(display_name, name, secondary_text, highlights)

        return DestinationSuggestion(
            id=str(item.get("placeId") or item.get("place") or display_name),
            name=name or display_name,
            country=country,
            region=region,
            display_name=display_name,
            description=description,
            highlights=highlights,
        )

    def _build_google_description(
        self, display_name: str, name: str, secondary_text: str, highlights: list[str]
    ) -> str:
        location_context = secondary_text or display_name or name
        if highlights:
            return f"{location_context}. Google suggests this match for {name or display_name} with cues like {', '.join(highlights[:2])}."
        return f"{location_context}. Google suggests this as a strong place match."

    def _build_google_highlights(
        self, raw_types: list[Any], region: str, country: str
    ) -> list[str]:
        ignored_types = {
            "establishment",
            "point_of_interest",
            "political",
            "geocode",
        }
        highlights: list[str] = []
        for value in raw_types:
            if not isinstance(value, str):
                continue
            cleaned = value.strip().lower()
            if not cleaned or cleaned in ignored_types:
                continue
            humanized = cleaned.replace("_", " ")
            if humanized not in highlights:
                highlights.append(humanized)
        for contextual_value in (region, country):
            cleaned = contextual_value.strip()
            if cleaned and cleaned.lower() not in {value.lower() for value in highlights}:
                highlights.append(cleaned)
        return highlights[:3]

    def _dedupe_suggestions(self, suggestions: list[DestinationSuggestion], limit: int) -> list[DestinationSuggestion]:
        deduped: list[DestinationSuggestion] = []
        seen: set[str] = set()
        for suggestion in suggestions:
            key = self._normalize(suggestion.display_name)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(suggestion)
            if len(deduped) >= limit:
                break
        return deduped

    def _apply_country_bias(
        self, suggestions: list[DestinationSuggestion], query: str, limit: int
    ) -> list[DestinationSuggestion]:
        normalized_query = self._normalize(query)
        explicit_non_india_terms = {
            "japan",
            "portugal",
            "france",
            "italy",
            "spain",
            "united kingdom",
            "uk",
            "united states",
            "usa",
            "uae",
            "thailand",
            "indonesia",
        }
        if any(term in normalized_query for term in explicit_non_india_terms):
            return suggestions[:limit]

        def rank_key(suggestion: DestinationSuggestion) -> tuple[int, int, str]:
            country = self._normalize(suggestion.country)
            region = self._normalize(suggestion.region)
            is_india = int(country == "india" or "india" in region)
            exact_prefix = int(self._normalize(suggestion.name).startswith(normalized_query))
            return (exact_prefix, is_india, suggestion.display_name)

        return sorted(suggestions, key=rank_key, reverse=True)[:limit]

    def _score(self, record: DestinationRecord, query: str) -> int:
        score = 0
        haystacks = [
            self._normalize(record.name),
            self._normalize(record.display_name),
            self._normalize(record.country),
            self._normalize(record.region),
            self._normalize(record.description),
        ]
        aliases = [self._normalize(alias) for alias in record.aliases]

        if self._normalize(record.name).startswith(query):
            score += 120
        elif self._normalize(record.display_name).startswith(query):
            score += 115

        if any(alias.startswith(query) for alias in aliases):
            score += 95

        if any(query in haystack for haystack in haystacks):
            score += 70

        for highlight in record.highlights:
            if query in self._normalize(highlight):
                score += 20

        query_tokens = query.split()
        name_tokens = self._normalize(record.name).split()
        if query_tokens and all(any(token.startswith(qt) for token in name_tokens) for qt in query_tokens):
            score += 35

        return score + record.popularity

    def _serialize_record(self, record: DestinationRecord) -> DestinationSuggestion:
        return DestinationSuggestion(
            id=record.id,
            name=record.name,
            country=record.country,
            region=record.region,
            display_name=record.display_name,
            description=record.description,
            highlights=list(record.highlights),
        )

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().replace(",", " ").split())
