from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    llm_provider_order: str = os.getenv("LLM_PROVIDER_ORDER", "gemini,groq,xai")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    gemini_base_url: str = os.getenv(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    )
    xai_api_key: str = os.getenv("XAI_API_KEY", os.getenv("GROK_API_KEY", ""))
    xai_model: str = os.getenv("XAI_MODEL", "grok-2-latest")
    xai_base_url: str = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    backend_origin: str = os.getenv("BACKEND_ORIGIN", "http://localhost:8000")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://travelcraft:travelcraft@localhost:5432/travelcraft_ai",
    )
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-local-dev")
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "travelcraft_session")
    auth_cookie_secure: bool = env_bool("AUTH_COOKIE_SECURE", False)
    auth_token_expire_hours: int = int(os.getenv("AUTH_TOKEN_EXPIRE_HOURS", "168"))
    exchange_rate_api_url: str = os.getenv("EXCHANGE_RATE_API_URL", "https://api.openexchangeapi.com/v1/latest")
    exchange_rate_api_key: str = os.getenv("EXCHANGE_RATE_API_KEY", "")
    exchange_rate_timeout_seconds: float = float(os.getenv("EXCHANGE_RATE_TIMEOUT_SECONDS", "10"))
    google_places_api_key: str = os.getenv("GOOGLE_PLACES_API_KEY", os.getenv("GOOGLE_MAPS_API_KEY", ""))
    google_places_autocomplete_url: str = os.getenv(
        "GOOGLE_PLACES_AUTOCOMPLETE_URL",
        "https://places.googleapis.com/v1/places:autocomplete",
    )
    google_places_region_code: str = os.getenv("GOOGLE_PLACES_REGION_CODE", "IN")
    google_places_language_code: str = os.getenv("GOOGLE_PLACES_LANGUAGE_CODE", "en")
    google_places_field_mask: str = os.getenv(
        "GOOGLE_PLACES_FIELD_MASK",
        ",".join(
            (
                "suggestions.placePrediction.place",
                "suggestions.placePrediction.placeId",
                "suggestions.placePrediction.text.text",
                "suggestions.placePrediction.structuredFormat.mainText.text",
                "suggestions.placePrediction.structuredFormat.secondaryText.text",
                "suggestions.placePrediction.types",
            )
        ),
    )
    destination_suggestions_timeout_seconds: float = float(
        os.getenv("DESTINATION_SUGGESTIONS_TIMEOUT_SECONDS", "10")
    )


settings = Settings()
