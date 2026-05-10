from __future__ import annotations

import httpx

from app.services.exchange_rate_service import ExchangeRateService


class FakeClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, _url: str, params: dict[str, str]):
        assert params["base"] == "INR"
        return httpx.Response(200, json=self.payload)


def test_fetch_latest_rates_normalizes_payload(monkeypatch) -> None:
    payload = {"rates": {"usd": 0.012, "JPY": 1.82}}
    monkeypatch.setattr("app.services.exchange_rate_service.httpx.Client", lambda timeout: FakeClient(payload))

    service = ExchangeRateService(api_url="https://example.test", api_key="", timeout_seconds=5)
    rates = service.fetch_latest_rates("INR")

    assert rates["USD"] == 0.012
    assert rates["JPY"] == 1.82
    assert rates["INR"] == 1.0


def test_convert_amount_to_inr_uses_inr_based_rates() -> None:
    service = ExchangeRateService(api_url="https://example.test", api_key="", timeout_seconds=5)
    rates = {"USD": 0.0125, "INR": 1.0}

    assert service.convert_amount_to_inr(100, "USD", rates) == 8000.0
    assert service.convert_amount_to_inr(2500, "INR", rates) == 2500.0
