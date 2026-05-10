"""lock trips to INR and convert legacy currencies"""

from __future__ import annotations

import copy

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.services.exchange_rate_service import ExchangeRateService


revision = "20260427_0003"
down_revision = "20260425_0002"
branch_labels = None
depends_on = None


TRIPS = sa.table(
    "trips",
    sa.column("id", postgresql.UUID(as_uuid=False)),
    sa.column("user_id", postgresql.UUID(as_uuid=False)),
    sa.column("budget", sa.Float()),
    sa.column("currency_code", sa.String()),
)

TRAVEL_PLANS = sa.table(
    "travel_plans",
    sa.column("id", postgresql.UUID(as_uuid=False)),
    sa.column("trip_id", postgresql.UUID(as_uuid=False)),
    sa.column("cost_estimation", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("ai_output", postgresql.JSONB(astext_type=sa.Text())),
    sa.column("prompt_snapshot", postgresql.JSONB(astext_type=sa.Text())),
)

ITINERARY_DAYS = sa.table(
    "itinerary_days",
    sa.column("travel_plan_id", postgresql.UUID(as_uuid=False)),
    sa.column("daily_budget_estimate", sa.Float()),
)

ITINERARY_ITEMS = sa.table(
    "itinerary_items",
    sa.column("itinerary_day_id", postgresql.UUID(as_uuid=False)),
    sa.column("estimated_cost", sa.Float()),
)

MEMORY_EVENTS = sa.table(
    "memory_events",
    sa.column("id", postgresql.UUID(as_uuid=False)),
    sa.column("user_id", postgresql.UUID(as_uuid=False)),
    sa.column("trip_id", postgresql.UUID(as_uuid=False)),
    sa.column("event_type", sa.String()),
    sa.column("event_value", postgresql.JSONB(astext_type=sa.Text())),
)

USER_PREFERENCES = sa.table(
    "user_preferences",
    sa.column("user_id", postgresql.UUID(as_uuid=False)),
    sa.column("budget_min", sa.Float()),
    sa.column("budget_max", sa.Float()),
)


def _convert_numeric_fields(payload: dict, factor: float, keys: tuple[str, ...]) -> dict:
    converted = copy.deepcopy(payload or {})
    for key in keys:
        value = converted.get(key)
        if isinstance(value, (int, float)):
            converted[key] = round(float(value) * factor, 2)
    return converted


def _convert_cost_breakdown(payload: dict | None, factor: float) -> dict:
    return _convert_numeric_fields(
        payload or {},
        factor,
        ("accommodation", "food", "transport", "activities", "contingency", "total"),
    )


def _convert_prompt_snapshot(payload: dict | None, factor: float) -> dict:
    converted = copy.deepcopy(payload or {})
    if isinstance(converted.get("budget"), (int, float)):
        converted["budget"] = round(float(converted["budget"]) * factor, 2)
    if "currency_code" in converted:
        converted["currency_code"] = "INR"

    submitted_request = converted.get("submitted_request")
    if isinstance(submitted_request, dict):
        if isinstance(submitted_request.get("budget"), (int, float)):
            submitted_request["budget"] = round(float(submitted_request["budget"]) * factor, 2)
        submitted_request["currency_code"] = "INR"
        converted["submitted_request"] = submitted_request

    return converted


def _convert_ai_output(payload: dict | None, factor: float) -> dict:
    converted = copy.deepcopy(payload or {})
    if isinstance(converted.get("budget"), (int, float)):
        converted["budget"] = round(float(converted["budget"]) * factor, 2)
    converted["currency_code"] = "INR"

    if isinstance(converted.get("cost_breakdown"), dict):
        converted["cost_breakdown"] = _convert_cost_breakdown(converted["cost_breakdown"], factor)

    attractions = converted.get("attractions")
    if isinstance(attractions, list):
        for item in attractions:
            if isinstance(item, dict) and isinstance(item.get("estimated_cost"), (int, float)):
                item["estimated_cost"] = round(float(item["estimated_cost"]) * factor, 2)

    itinerary = converted.get("itinerary")
    if isinstance(itinerary, list):
        for day in itinerary:
            if not isinstance(day, dict):
                continue
            if isinstance(day.get("daily_estimate"), (int, float)):
                day["daily_estimate"] = round(float(day["daily_estimate"]) * factor, 2)
            activities = day.get("activities")
            if isinstance(activities, list):
                for activity in activities:
                    if isinstance(activity, dict) and isinstance(activity.get("estimated_cost"), (int, float)):
                        activity["estimated_cost"] = round(float(activity["estimated_cost"]) * factor, 2)

    return converted


def upgrade() -> None:
    op.alter_column("trips", "currency_code", server_default="INR")

    connection = op.get_bind()
    trip_rows = list(
        connection.execute(
            sa.select(
                TRIPS.c.id,
                TRIPS.c.user_id,
                TRIPS.c.budget,
                TRIPS.c.currency_code,
                TRAVEL_PLANS.c.id.label("travel_plan_id"),
                TRAVEL_PLANS.c.cost_estimation,
                TRAVEL_PLANS.c.ai_output,
                TRAVEL_PLANS.c.prompt_snapshot,
            ).select_from(
                TRIPS.outerjoin(TRAVEL_PLANS, TRAVEL_PLANS.c.trip_id == TRIPS.c.id)
            )
            .where(TRIPS.c.currency_code != "INR")
        ).mappings()
    )

    if not trip_rows:
        return

    rate_service = ExchangeRateService()
    inr_rates = rate_service.fetch_latest_rates("INR")

    latest_user_factor: dict[str, float] = {}

    for row in trip_rows:
        factor = rate_service.inr_conversion_factor(row["currency_code"], inr_rates)
        latest_user_factor[str(row["user_id"])] = factor
        converted_budget = round(float(row["budget"]) * factor, 2)

        connection.execute(
            sa.update(TRIPS)
            .where(TRIPS.c.id == row["id"])
            .values(budget=converted_budget, currency_code="INR")
        )

        if row["travel_plan_id"]:
            connection.execute(
                sa.update(TRAVEL_PLANS)
                .where(TRAVEL_PLANS.c.id == row["travel_plan_id"])
                .values(
                    cost_estimation=_convert_cost_breakdown(row["cost_estimation"], factor),
                    ai_output=_convert_ai_output(row["ai_output"], factor),
                    prompt_snapshot=_convert_prompt_snapshot(row["prompt_snapshot"], factor),
                )
            )

            connection.execute(
                sa.text(
                    """
                    UPDATE itinerary_days
                    SET daily_budget_estimate = ROUND((daily_budget_estimate * :factor)::numeric, 2)
                    WHERE travel_plan_id = :travel_plan_id AND daily_budget_estimate IS NOT NULL
                    """
                ),
                {"factor": factor, "travel_plan_id": row["travel_plan_id"]},
            )

            connection.execute(
                sa.text(
                    """
                    UPDATE itinerary_items
                    SET estimated_cost = ROUND((estimated_cost * :factor)::numeric, 2)
                    WHERE itinerary_day_id IN (
                        SELECT id FROM itinerary_days WHERE travel_plan_id = :travel_plan_id
                    )
                    AND estimated_cost IS NOT NULL
                    """
                ),
                {"factor": factor, "travel_plan_id": row["travel_plan_id"]},
            )

        event_rows = list(
            connection.execute(
                sa.select(MEMORY_EVENTS.c.id, MEMORY_EVENTS.c.event_value)
                .where(
                    sa.and_(
                        MEMORY_EVENTS.c.trip_id == row["id"],
                        MEMORY_EVENTS.c.event_type == "trip_generation",
                    )
                )
            ).mappings()
        )
        for event_row in event_rows:
            payload = copy.deepcopy(event_row["event_value"] or {})
            if isinstance(payload.get("budget"), (int, float)):
                payload["budget"] = round(float(payload["budget"]) * factor, 2)
            payload["currency_code"] = "INR"
            connection.execute(
                sa.update(MEMORY_EVENTS)
                .where(MEMORY_EVENTS.c.id == event_row["id"])
                .values(event_value=payload)
            )

    for user_id, factor in latest_user_factor.items():
        connection.execute(
            sa.text(
                """
                UPDATE user_preferences
                SET
                    budget_min = CASE WHEN budget_min IS NULL THEN NULL ELSE ROUND((budget_min * :factor)::numeric, 2) END,
                    budget_max = CASE WHEN budget_max IS NULL THEN NULL ELSE ROUND((budget_max * :factor)::numeric, 2) END
                WHERE user_id = :user_id
                """
            ),
            {"factor": factor, "user_id": user_id},
        )


def downgrade() -> None:
    op.alter_column("trips", "currency_code", server_default="USD")
