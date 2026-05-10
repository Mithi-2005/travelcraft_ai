from __future__ import annotations

from app.services.firecrawl_service import FirecrawlService


def test_infer_best_time_varies_by_destination() -> None:
    service = FirecrawlService()

    tirupati_time = service._infer_best_time("Tirumala, Tirupati, Andhra Pradesh", [])
    tokyo_time = service._infer_best_time("Tokyo, Japan", [])

    assert tirupati_time != tokyo_time
    assert "October to February" in tirupati_time
    assert "March to May" in tokyo_time


def test_infer_best_time_uses_live_month_range_when_present() -> None:
    service = FirecrawlService()

    hint = service._infer_best_time(
        "Lisbon, Portugal",
        [
            "Travel guide: The best time to visit is April to June for mild weather and lighter crowds."
        ],
    )

    assert hint == "April to June (based on current destination travel guidance)"
