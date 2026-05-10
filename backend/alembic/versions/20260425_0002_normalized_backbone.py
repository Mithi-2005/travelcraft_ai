"""normalize travel backbone schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260425_0002"
down_revision = "20260422_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("UPDATE users SET email = lower(trim(email))")
    op.execute("DROP INDEX IF EXISTS ix_users_email")
    op.execute("ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_user_id_fkey")
    op.execute("ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_user_id_fkey")
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=24), server_default="traveler", nullable=False),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('traveler', 'admin')")
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE uuid USING id::uuid")
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))")

    op.rename_table("user_profiles", "user_preferences")
    op.rename_table("trips", "trips_legacy")
    op.execute("DROP INDEX IF EXISTS ix_trips_destination")
    op.execute("DROP INDEX IF EXISTS ix_trips_user_id")

    op.execute("ALTER TABLE user_preferences ALTER COLUMN user_id TYPE uuid USING user_id::uuid")
    op.execute("ALTER TABLE user_preferences ADD CONSTRAINT user_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE trips_legacy ALTER COLUMN user_id TYPE uuid USING user_id::uuid")

    op.add_column("user_preferences", sa.Column("budget_min", sa.Float(), nullable=True))
    op.add_column("user_preferences", sa.Column("budget_max", sa.Float(), nullable=True))
    op.add_column(
        "user_preferences",
        sa.Column("travel_style_notes", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "user_preferences",
        sa.Column("trip_mood", sa.String(length=24), server_default="relaxed", nullable=False),
    )
    op.add_column(
        "user_preferences",
        sa.Column("preferred_transport", sa.String(length=24), server_default="mixed", nullable=False),
    )
    op.add_column(
        "user_preferences",
        sa.Column("accommodation_type", sa.String(length=24), server_default="mixed", nullable=False),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "language_preferences",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "dietary_preferences",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "accessibility_needs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "interests_new",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE user_preferences
        SET
            budget_min = budget_preference,
            budget_max = budget_preference,
            travel_style_notes = COALESCE(travel_style, ''),
            travel_style = CASE
                WHEN lower(trim(travel_style)) IN ('budget', 'balanced', 'premium', 'luxury') THEN lower(trim(travel_style))
                WHEN lower(travel_style) LIKE '%luxury%' THEN 'luxury'
                WHEN lower(travel_style) LIKE '%premium%' OR lower(travel_style) LIKE '%boutique%' THEN 'premium'
                WHEN lower(travel_style) LIKE '%budget%' OR lower(travel_style) LIKE '%cheap%' OR lower(travel_style) LIKE '%affordable%' THEN 'budget'
                ELSE 'balanced'
            END,
            trip_mood = CASE
                WHEN preferred_mood IN ('relaxed', 'adventure', 'luxury', 'culture', 'family', 'romantic') THEN preferred_mood
                ELSE 'relaxed'
            END,
            interests_new = COALESCE(
                ARRAY(SELECT jsonb_array_elements_text(COALESCE(interests, '[]'::jsonb))),
                ARRAY[]::text[]
            )
        """
    )

    op.drop_column("user_preferences", "interests")
    op.alter_column("user_preferences", "interests_new", new_column_name="interests")
    op.drop_column("user_preferences", "budget_preference")
    op.drop_column("user_preferences", "preferred_mood")

    op.create_check_constraint(
        "ck_user_preferences_budget_min",
        "user_preferences",
        "budget_min IS NULL OR budget_min >= 0",
    )
    op.create_check_constraint(
        "ck_user_preferences_budget_max_positive",
        "user_preferences",
        "budget_max IS NULL OR budget_max >= 0",
    )
    op.create_check_constraint(
        "ck_user_preferences_budget_range",
        "user_preferences",
        "budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min",
    )
    op.create_check_constraint(
        "ck_user_preferences_travel_style",
        "user_preferences",
        "travel_style IN ('budget', 'balanced', 'premium', 'luxury')",
    )
    op.create_check_constraint(
        "ck_user_preferences_trip_mood",
        "user_preferences",
        "trip_mood IN ('relaxed', 'adventure', 'luxury', 'culture', 'family', 'romantic')",
    )
    op.create_check_constraint(
        "ck_user_preferences_preferred_transport",
        "user_preferences",
        "preferred_transport IN ('flight', 'train', 'roadtrip', 'mixed')",
    )
    op.create_check_constraint(
        "ck_user_preferences_accommodation_type",
        "user_preferences",
        "accommodation_type IN ('hostel', 'hotel', 'boutique', 'resort', 'apartment', 'mixed')",
    )

    op.create_table(
        "trips",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("legacy_trip_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=255), server_default="", nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("destination_country", sa.String(length=128), server_default="", nullable=False),
        sa.Column("origin_airport", sa.String(length=16), server_default="", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("traveler_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_trip_key", name="uq_trips_legacy_trip_key"),
        sa.UniqueConstraint("id", "user_id", name="uq_trips_id_user_id"),
        sa.CheckConstraint(
            "status IN ('draft', 'researching', 'planned', 'booked', 'completed', 'cancelled')",
            name="ck_trips_status",
        ),
        sa.CheckConstraint("budget >= 0", name="ck_trips_budget"),
        sa.CheckConstraint("traveler_count >= 1", name="ck_trips_traveler_count"),
        sa.CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="ck_trips_currency_code"),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_trips_date_range",
        ),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"], unique=False)
    op.create_index("ix_trips_status", "trips", ["status"], unique=False)
    op.create_index("ix_trips_destination", "trips", ["destination"], unique=False)
    op.create_index("ix_trips_start_date", "trips", ["start_date"], unique=False)
    op.create_index("ix_trips_created_at", "trips", ["created_at"], unique=False)

    op.create_table(
        "travel_plans",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("generated_by_model", sa.String(length=120), server_default="", nullable=False),
        sa.Column("generation_provider", sa.String(length=60), server_default="", nullable=False),
        sa.Column("prompt_snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("ai_output", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("best_time_to_visit", sa.Text(), nullable=False),
        sa.Column("cost_estimation", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("source_data", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("research_mode", sa.String(length=24), server_default="fallback", nullable=False),
        sa.Column("llm_mode", sa.String(length=24), server_default="fallback", nullable=False),
        sa.Column("research_error", sa.Text(), nullable=True),
        sa.Column("llm_error", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", name="uq_travel_plans_trip_id"),
        sa.CheckConstraint("research_mode IN ('live', 'fallback')", name="ck_travel_plans_research_mode"),
        sa.CheckConstraint("llm_mode IN ('live', 'fallback')", name="ck_travel_plans_llm_mode"),
    )
    op.create_index("ix_travel_plans_trip_id", "travel_plans", ["trip_id"], unique=False)

    op.create_table(
        "itinerary_days",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("travel_plan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=True),
        sa.Column("theme", sa.String(length=255), server_default="", nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("daily_budget_estimate", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["travel_plan_id"], ["travel_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("travel_plan_id", "day_number", name="uq_itinerary_days_trip_day"),
        sa.UniqueConstraint("travel_plan_id", "calendar_date", name="uq_itinerary_days_trip_date"),
        sa.CheckConstraint("day_number >= 1", name="ck_itinerary_days_day_number"),
        sa.CheckConstraint(
            "daily_budget_estimate IS NULL OR daily_budget_estimate >= 0",
            name="ck_itinerary_days_budget",
        ),
    )
    op.create_index("ix_itinerary_days_travel_plan_id", "itinerary_days", ["travel_plan_id"], unique=False)

    op.create_table(
        "itinerary_items",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("itinerary_day_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location_name", sa.String(length=255), server_default="", nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("booking_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["itinerary_day_id"], ["itinerary_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("itinerary_day_id", "sort_order", name="uq_itinerary_items_day_sort"),
        sa.CheckConstraint("sort_order >= 1", name="ck_itinerary_items_sort_order"),
        sa.CheckConstraint(
            "item_type IN ('activity', 'meal', 'transport', 'stay', 'note')",
            name="ck_itinerary_items_item_type",
        ),
        sa.CheckConstraint("duration_minutes IS NULL OR duration_minutes > 0", name="ck_itinerary_items_duration"),
        sa.CheckConstraint("estimated_cost IS NULL OR estimated_cost >= 0", name="ck_itinerary_items_estimated_cost"),
        sa.CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR end_time > start_time",
            name="ck_itinerary_items_time_order",
        ),
    )
    op.create_index("ix_itinerary_items_itinerary_day_id", "itinerary_items", ["itinerary_day_id"], unique=False)

    op.create_table(
        "destination_research",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.String(length=255), server_default="", nullable=False),
        sa.Column("content_type", sa.String(length=24), server_default="other", nullable=False),
        sa.Column("title", sa.Text(), server_default="", nullable=False),
        sa.Column("scraped_text", sa.Text(), server_default="", nullable=False),
        sa.Column("summary_text", sa.Text(), server_default="", nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "source_url", name="uq_destination_research_trip_url"),
        sa.CheckConstraint(
            "content_type IN ('guide', 'attraction', 'itinerary', 'blog', 'map', 'other')",
            name="ck_destination_research_content_type",
        ),
    )
    op.create_index("ix_destination_research_trip_id", "destination_research", ["trip_id"], unique=False)
    op.create_index("ix_destination_research_source_domain", "destination_research", ["source_domain"], unique=False)
    op.create_index("ix_destination_research_scraped_at", "destination_research", ["scraped_at"], unique=False)

    op.create_table(
        "memory_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_key", sa.String(length=120), nullable=False),
        sa.Column("event_value", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "event_type IN ('preference_update', 'behavior_signal', 'trip_generation', 'feedback_learning', 'system_inference')",
            name="ck_memory_events_event_type",
        ),
        sa.CheckConstraint(
            "source IN ('user', 'llm', 'firecrawl', 'system')",
            name="ck_memory_events_source",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_memory_events_confidence_score",
        ),
    )
    op.create_index("ix_memory_events_user_id", "memory_events", ["user_id"], unique=False)
    op.create_index("ix_memory_events_trip_id", "memory_events", ["trip_id"], unique=False)
    op.create_index("ix_memory_events_event_type", "memory_events", ["event_type"], unique=False)
    op.create_index("ix_memory_events_recorded_at", "memory_events", ["recorded_at"], unique=False)

    op.create_table(
        "trip_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=False), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("itinerary_rating", sa.Integer(), nullable=False),
        sa.Column("accuracy_rating", sa.Integer(), nullable=False),
        sa.Column("value_rating", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text(), server_default="", nullable=False),
        sa.Column("liked_points", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("disliked_points", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
        sa.Column("would_reuse", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id", "user_id"], ["trips.id", "trips.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "user_id", name="uq_trip_feedback_trip_user"),
        sa.CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_trip_feedback_overall_rating"),
        sa.CheckConstraint("itinerary_rating BETWEEN 1 AND 5", name="ck_trip_feedback_itinerary_rating"),
        sa.CheckConstraint("accuracy_rating BETWEEN 1 AND 5", name="ck_trip_feedback_accuracy_rating"),
        sa.CheckConstraint("value_rating BETWEEN 1 AND 5", name="ck_trip_feedback_value_rating"),
    )
    op.create_index("ix_trip_feedback_trip_id", "trip_feedback", ["trip_id"], unique=False)
    op.create_index("ix_trip_feedback_user_id", "trip_feedback", ["user_id"], unique=False)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for table_name in (
        "users",
        "user_preferences",
        "trips",
        "travel_plans",
        "itinerary_days",
        "itinerary_items",
        "destination_research",
        "memory_events",
        "trip_feedback",
    ):
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS trg_{table_name}_updated_at ON {table_name};
            CREATE TRIGGER trg_{table_name}_updated_at
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )

    op.execute(
        """
        INSERT INTO trips (
            legacy_trip_key,
            user_id,
            title,
            destination,
            destination_country,
            origin_airport,
            start_date,
            end_date,
            budget,
            currency_code,
            status,
            notes,
            traveler_count,
            created_at,
            updated_at
        )
        SELECT
            trip_id,
            user_id,
            destination,
            destination,
            '',
            '',
            NULL,
            NULL,
            budget,
            'USD',
            'planned',
            COALESCE(overview, ''),
            1,
            COALESCE(generated_at, now()),
            COALESCE(generated_at, now())
        FROM trips_legacy
        """
    )

    op.execute(
        """
        INSERT INTO travel_plans (
            trip_id,
            generated_by_model,
            generation_provider,
            prompt_snapshot,
            ai_output,
            overview,
            best_time_to_visit,
            cost_estimation,
            source_data,
            research_mode,
            llm_mode,
            research_error,
            llm_error,
            generated_at,
            created_at,
            updated_at
        )
        SELECT
            t.id,
            'legacy-import',
            CASE WHEN tl.llm_mode = 'live' THEN 'openai' ELSE 'fallback' END,
            '{}'::jsonb,
            jsonb_build_object(
                'trip_id', tl.trip_id,
                'destination', tl.destination,
                'budget', tl.budget,
                'interests', tl.interests,
                'mood', tl.mood,
                'generated_at', tl.generated_at,
                'overview', tl.overview,
                'best_time_to_visit', tl.best_time_to_visit,
                'live_insights', tl.live_insights,
                'attractions', tl.attractions,
                'itinerary', tl.itinerary,
                'cost_breakdown', tl.cost_breakdown,
                'smart_suggestions', tl.smart_suggestions,
                'research_mode', tl.research_mode,
                'research_error', tl.research_error,
                'research_sources', tl.research_sources,
                'llm_mode', tl.llm_mode,
                'llm_error', tl.llm_error,
                'highlight', tl.highlight
            ),
            tl.overview,
            tl.best_time_to_visit,
            COALESCE(tl.cost_breakdown, '{}'::jsonb),
            jsonb_build_object(
                'live_insights', COALESCE(tl.live_insights, '[]'::jsonb),
                'research_sources', COALESCE(tl.research_sources, '[]'::jsonb),
                'research_mode', tl.research_mode
            ),
            tl.research_mode,
            tl.llm_mode,
            tl.research_error,
            tl.llm_error,
            tl.generated_at,
            COALESCE(tl.generated_at, now()),
            COALESCE(tl.generated_at, now())
        FROM trips_legacy tl
        JOIN trips t ON t.legacy_trip_key = tl.trip_id
        """
    )

    op.execute(
        """
        WITH day_rows AS (
            SELECT
                tp.id AS travel_plan_id,
                day_entry.value AS day_json,
                day_entry.ordinality AS day_ordinality
            FROM trips_legacy tl
            JOIN trips t ON t.legacy_trip_key = tl.trip_id
            JOIN travel_plans tp ON tp.trip_id = t.id
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(tl.itinerary, '[]'::jsonb)) WITH ORDINALITY AS day_entry(value, ordinality)
        )
        INSERT INTO itinerary_days (
            travel_plan_id,
            day_number,
            calendar_date,
            theme,
            summary,
            daily_budget_estimate,
            created_at,
            updated_at
        )
        SELECT
            travel_plan_id,
            COALESCE(NULLIF(day_json->>'day', '')::int, day_ordinality::int),
            NULL,
            COALESCE(day_json->>'theme', ''),
            COALESCE(day_json->>'summary', ''),
            CASE
                WHEN COALESCE(day_json->>'daily_estimate', '') = '' THEN NULL
                ELSE (day_json->>'daily_estimate')::double precision
            END,
            now(),
            now()
        FROM day_rows
        """
    )

    op.execute(
        """
        WITH day_rows AS (
            SELECT
                tp.id AS travel_plan_id,
                day_entry.value AS day_json,
                COALESCE(NULLIF(day_entry.value->>'day', '')::int, day_entry.ordinality::int) AS day_number
            FROM trips_legacy tl
            JOIN trips t ON t.legacy_trip_key = tl.trip_id
            JOIN travel_plans tp ON tp.trip_id = t.id
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(tl.itinerary, '[]'::jsonb)) WITH ORDINALITY AS day_entry(value, ordinality)
        ),
        activity_rows AS (
            SELECT
                d.id AS itinerary_day_id,
                act.value AS activity_json,
                act.ordinality AS sort_order
            FROM day_rows dr
            JOIN itinerary_days d
                ON d.travel_plan_id = dr.travel_plan_id
               AND d.day_number = dr.day_number
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(dr.day_json->'activities', '[]'::jsonb)) WITH ORDINALITY AS act(value, ordinality)
        )
        INSERT INTO itinerary_items (
            itinerary_day_id,
            sort_order,
            item_type,
            title,
            location_name,
            start_time,
            end_time,
            duration_minutes,
            estimated_cost,
            booking_required,
            tags,
            details,
            created_at,
            updated_at
        )
        SELECT
            itinerary_day_id,
            sort_order::int,
            'activity',
            COALESCE(activity_json->>'title', ''),
            COALESCE(activity_json->>'location', ''),
            CASE
                WHEN COALESCE(activity_json->>'time', '') ~ '^[0-9]{2}:[0-9]{2}$' THEN (activity_json->>'time')::time
                ELSE NULL
            END,
            NULL,
            NULL,
            CASE
                WHEN COALESCE(activity_json->>'estimated_cost', '') = '' THEN NULL
                ELSE (activity_json->>'estimated_cost')::double precision
            END,
            FALSE,
            ARRAY[]::text[],
            jsonb_build_object('description', COALESCE(activity_json->>'description', '')),
            now(),
            now()
        FROM activity_rows
        """
    )

    op.execute(
        """
        WITH day_rows AS (
            SELECT
                tp.id AS travel_plan_id,
                day_entry.value AS day_json,
                COALESCE(NULLIF(day_entry.value->>'day', '')::int, day_entry.ordinality::int) AS day_number,
                COALESCE(jsonb_array_length(COALESCE(day_entry.value->'activities', '[]'::jsonb)), 0) AS activity_count
            FROM trips_legacy tl
            JOIN trips t ON t.legacy_trip_key = tl.trip_id
            JOIN travel_plans tp ON tp.trip_id = t.id
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(tl.itinerary, '[]'::jsonb)) WITH ORDINALITY AS day_entry(value, ordinality)
        ),
        meal_rows AS (
            SELECT
                d.id AS itinerary_day_id,
                meals.value #>> '{}' AS meal_title,
                dr.activity_count + meals.ordinality AS sort_order
            FROM day_rows dr
            JOIN itinerary_days d
                ON d.travel_plan_id = dr.travel_plan_id
               AND d.day_number = dr.day_number
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(dr.day_json->'meals', '[]'::jsonb)) WITH ORDINALITY AS meals(value, ordinality)
        )
        INSERT INTO itinerary_items (
            itinerary_day_id,
            sort_order,
            item_type,
            title,
            location_name,
            start_time,
            end_time,
            duration_minutes,
            estimated_cost,
            booking_required,
            tags,
            details,
            created_at,
            updated_at
        )
        SELECT
            itinerary_day_id,
            sort_order::int,
            'meal',
            meal_title,
            '',
            NULL,
            NULL,
            NULL,
            NULL,
            FALSE,
            ARRAY[]::text[],
            '{}'::jsonb,
            now(),
            now()
        FROM meal_rows
        """
    )

    op.execute(
        """
        WITH source_rows AS (
            SELECT
                t.id AS trip_id,
                tl.generated_at,
                src.value AS source_json
            FROM trips_legacy tl
            JOIN trips t ON t.legacy_trip_key = tl.trip_id
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(tl.research_sources, '[]'::jsonb)) AS src(value)
        )
        INSERT INTO destination_research (
            trip_id,
            source_url,
            source_domain,
            content_type,
            title,
            scraped_text,
            summary_text,
            tags,
            metadata,
            scraped_at,
            created_at,
            updated_at
        )
        SELECT
            trip_id,
            COALESCE(source_json->>'url', ''),
            COALESCE(source_json->>'domain', ''),
            'guide',
            COALESCE(source_json->>'title', ''),
            '',
            COALESCE(source_json->>'snippet', ''),
            ARRAY[]::text[],
            source_json,
            COALESCE(generated_at, now()),
            now(),
            now()
        FROM source_rows
        WHERE COALESCE(source_json->>'url', '') <> ''
        """
    )

    op.execute(
        """
        INSERT INTO memory_events (
            user_id,
            trip_id,
            event_type,
            event_key,
            event_value,
            source,
            confidence_score,
            recorded_at,
            created_at,
            updated_at
        )
        SELECT
            up.user_id,
            NULL,
            'preference_update',
            'preference_seed',
            jsonb_build_object(
                'budget_min', up.budget_min,
                'budget_max', up.budget_max,
                'interests', up.interests,
                'trip_mood', up.trip_mood,
                'travel_style', up.travel_style,
                'travel_style_notes', up.travel_style_notes
            ),
            'system',
            1.0,
            now(),
            now(),
            now()
        FROM user_preferences up
        """
    )

    op.execute(
        """
        INSERT INTO memory_events (
            user_id,
            trip_id,
            event_type,
            event_key,
            event_value,
            source,
            confidence_score,
            recorded_at,
            created_at,
            updated_at
        )
        SELECT
            t.user_id,
            t.id,
            'trip_generation',
            'trip_generation',
            jsonb_build_object(
                'trip_id', t.legacy_trip_key,
                'destination', t.destination,
                'budget', t.budget,
                'status', t.status
            ),
            'system',
            1.0,
            COALESCE(tp.generated_at, t.created_at),
            now(),
            now()
        FROM trips t
        JOIN travel_plans tp ON tp.trip_id = t.id
        """
    )

    op.drop_table("trips_legacy")


def downgrade() -> None:
    op.create_table(
        "trips_legacy",
        sa.Column("trip_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column("interests", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("mood", sa.String(length=24), nullable=False),
        sa.Column("highlight", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("best_time_to_visit", sa.Text(), nullable=False),
        sa.Column("live_insights", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("attractions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("itinerary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("cost_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("smart_suggestions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("research_mode", sa.String(length=24), nullable=False, server_default="fallback"),
        sa.Column("research_error", sa.Text(), nullable=True),
        sa.Column("research_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("llm_mode", sa.String(length=24), nullable=False, server_default="fallback"),
        sa.Column("llm_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("trip_id"),
    )

    op.execute(
        """
        INSERT INTO trips_legacy (
            trip_id, user_id, destination, budget, interests, mood, highlight, generated_at,
            overview, best_time_to_visit, live_insights, attractions, itinerary, cost_breakdown,
            smart_suggestions, research_mode, research_error, research_sources, llm_mode, llm_error
        )
        SELECT
            t.legacy_trip_key,
            t.user_id,
            t.destination,
            t.budget,
            COALESCE(tp.ai_output->'interests', '[]'::jsonb),
            COALESCE(tp.ai_output->>'mood', 'relaxed'),
            COALESCE(tp.ai_output->>'highlight', ''),
            tp.generated_at,
            tp.overview,
            tp.best_time_to_visit,
            COALESCE(tp.ai_output->'live_insights', '[]'::jsonb),
            COALESCE(tp.ai_output->'attractions', '[]'::jsonb),
            COALESCE(tp.ai_output->'itinerary', '[]'::jsonb),
            COALESCE(tp.cost_estimation, '{}'::jsonb),
            COALESCE(tp.ai_output->'smart_suggestions', '[]'::jsonb),
            tp.research_mode,
            tp.research_error,
            COALESCE(tp.source_data->'research_sources', '[]'::jsonb),
            tp.llm_mode,
            tp.llm_error
        FROM trips t
        JOIN travel_plans tp ON tp.trip_id = t.id
        """
    )

    for table_name in (
        "trip_feedback",
        "memory_events",
        "destination_research",
        "itinerary_items",
        "itinerary_days",
        "travel_plans",
        "trips",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_updated_at ON {table_name}")

    op.drop_table("trip_feedback")
    op.drop_table("memory_events")
    op.drop_table("destination_research")
    op.drop_table("itinerary_items")
    op.drop_table("itinerary_days")
    op.drop_table("travel_plans")
    op.rename_table("trips_legacy", "trips")
    op.create_index("ix_trips_destination", "trips", ["destination"], unique=False)
    op.create_index("ix_trips_user_id", "trips", ["user_id"], unique=False)

    op.drop_constraint("ck_user_preferences_accommodation_type", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_preferred_transport", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_trip_mood", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_travel_style", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_budget_range", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_budget_max_positive", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_budget_min", "user_preferences", type_="check")

    op.add_column("user_preferences", sa.Column("budget_preference", sa.Float(), nullable=True))
    op.add_column("user_preferences", sa.Column("preferred_mood", sa.String(length=24), server_default="relaxed", nullable=False))
    op.add_column(
        "user_preferences",
        sa.Column("interests_old", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.execute(
        """
        UPDATE user_preferences
        SET
            budget_preference = COALESCE(budget_max, budget_min),
            preferred_mood = CASE
                WHEN trip_mood IN ('relaxed', 'adventure', 'luxury') THEN trip_mood
                ELSE 'relaxed'
            END,
            interests_old = to_jsonb(COALESCE(interests, ARRAY[]::text[]))
        """
    )
    op.drop_column("user_preferences", "interests")
    op.alter_column("user_preferences", "interests_old", new_column_name="interests")
    op.drop_column("user_preferences", "accessibility_needs")
    op.drop_column("user_preferences", "dietary_preferences")
    op.drop_column("user_preferences", "language_preferences")
    op.drop_column("user_preferences", "accommodation_type")
    op.drop_column("user_preferences", "preferred_transport")
    op.drop_column("user_preferences", "trip_mood")
    op.drop_column("user_preferences", "travel_style_notes")
    op.drop_column("user_preferences", "budget_max")
    op.drop_column("user_preferences", "budget_min")
    op.rename_table("user_preferences", "user_profiles")

    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE varchar(36) USING id::text")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
