from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


class ExchangeRateServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class ExchangeRateService:
    api_url: str = settings.exchange_rate_api_url
    api_key: str = settings.exchange_rate_api_key
    timeout_seconds: float = settings.exchange_rate_timeout_seconds

    def fetch_latest_rates(self, base_currency: str = "INR") -> dict[str, float]:
        params: dict[str, str] = {"base": base_currency}
        if self.api_key:
            params["apiKey"] = self.api_key

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(self.api_url, params=params)
            if response.status_code >= 400:
                raise ExchangeRateServiceError(
                    f"Exchange-rate provider request failed with status {response.status_code}."
                )

        payload = response.json()
        rates = payload.get("rates")
        if not isinstance(rates, dict) or not rates:
            raise ExchangeRateServiceError("Exchange-rate provider returned no usable rates.")

        normalized: dict[str, float] = {}
        for code, value in rates.items():
            try:
                normalized[str(code).upper()] = float(value)
            except (TypeError, ValueError):
                continue

        normalized[base_currency.upper()] = 1.0
        return normalized

    def inr_conversion_factor(self, from_currency: str, inr_based_rates: dict[str, float]) -> float:
        normalized_currency = from_currency.upper()
        if normalized_currency == "INR":
            return 1.0

        rate = inr_based_rates.get(normalized_currency)
        if rate is None or rate <= 0:
            raise ExchangeRateServiceError(f"Missing INR conversion rate for {normalized_currency}.")
        return 1 / rate

    def convert_amount_to_inr(self, amount: float | int | None, from_currency: str, inr_based_rates: dict[str, float]) -> float | None:
        if amount is None:
            return None
        factor = self.inr_conversion_factor(from_currency, inr_based_rates)
        return round(float(amount) * factor, 2)
