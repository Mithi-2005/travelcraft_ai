from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


UUID_TYPE = UUID(as_uuid=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('traveler', 'admin')", name="ck_users_role"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(24), default="traveler", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    preference: Mapped["UserPreference"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    trips: Mapped[list["Trip"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    memory_events: Mapped[list["MemoryEvent"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    feedback_entries: Mapped[list["TripFeedback"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        overlaps="feedback_entries,trip",
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint("budget_min IS NULL OR budget_min >= 0", name="ck_user_preferences_budget_min"),
        CheckConstraint(
            "budget_max IS NULL OR budget_max >= 0 OR budget_max IS NULL",
            name="ck_user_preferences_budget_max_positive",
        ),
        CheckConstraint(
            "budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min",
            name="ck_user_preferences_budget_range",
        ),
        CheckConstraint(
            "travel_style IN ('budget', 'balanced', 'premium', 'luxury')",
            name="ck_user_preferences_travel_style",
        ),
        CheckConstraint(
            "trip_mood IN ('relaxed', 'adventure', 'luxury', 'culture', 'family', 'romantic')",
            name="ck_user_preferences_trip_mood",
        ),
        CheckConstraint(
            "preferred_transport IN ('flight', 'train', 'roadtrip', 'mixed')",
            name="ck_user_preferences_preferred_transport",
        ),
        CheckConstraint(
            "accommodation_type IN ('hostel', 'hotel', 'boutique', 'resort', 'apartment', 'mixed')",
            name="ck_user_preferences_accommodation_type",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    interests: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    travel_style: Mapped[str] = mapped_column(String(24), default="balanced", nullable=False)
    travel_style_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    trip_mood: Mapped[str] = mapped_column(String(24), default="relaxed", nullable=False)
    preferred_transport: Mapped[str] = mapped_column(String(24), default="mixed", nullable=False)
    accommodation_type: Mapped[str] = mapped_column(String(24), default="mixed", nullable=False)
    home_airport: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    language_preferences: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    dietary_preferences: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    accessibility_needs: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="preference")


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        UniqueConstraint("legacy_trip_key", name="uq_trips_legacy_trip_key"),
        UniqueConstraint("id", "user_id", name="uq_trips_id_user_id"),
        CheckConstraint(
            "status IN ('draft', 'researching', 'planned', 'booked', 'completed', 'cancelled')",
            name="ck_trips_status",
        ),
        CheckConstraint("budget >= 0", name="ck_trips_budget"),
        CheckConstraint("traveler_count >= 1", name="ck_trips_traveler_count"),
        CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'",
            name="ck_trips_currency_code",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_trips_date_range",
        ),
        Index("ix_trips_user_id", "user_id"),
        Index("ix_trips_status", "status"),
        Index("ix_trips_destination", "destination"),
        Index("ix_trips_start_date", "start_date"),
        Index("ix_trips_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    legacy_trip_key: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    origin_airport: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    traveler_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="trips")
    travel_plan: Mapped["TravelPlan | None"] = relationship(
        back_populates="trip",
        uselist=False,
        cascade="all, delete-orphan",
    )
    research_documents: Mapped[list["DestinationResearch"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    memory_events: Mapped[list["MemoryEvent"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    feedback_entries: Mapped[list["TripFeedback"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        overlaps="feedback_entries,user",
    )


class TravelPlan(Base):
    __tablename__ = "travel_plans"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uq_travel_plans_trip_id"),
        CheckConstraint(
            "research_mode IN ('live', 'fallback')",
            name="ck_travel_plans_research_mode",
        ),
        CheckConstraint(
            "llm_mode IN ('live', 'fallback')",
            name="ck_travel_plans_llm_mode",
        ),
        Index("ix_travel_plans_trip_id", "trip_id"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    trip_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    generated_by_model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    generation_provider: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    prompt_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    ai_output: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    best_time_to_visit: Mapped[str] = mapped_column(Text, nullable=False)
    cost_estimation: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    source_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    research_mode: Mapped[str] = mapped_column(String(24), default="fallback", nullable=False)
    llm_mode: Mapped[str] = mapped_column(String(24), default="fallback", nullable=False)
    research_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trip: Mapped[Trip] = relationship(back_populates="travel_plan")
    itinerary_days: Mapped[list["ItineraryDay"]] = relationship(
        back_populates="travel_plan",
        cascade="all, delete-orphan",
        order_by="ItineraryDay.day_number",
    )


class ItineraryDay(Base):
    __tablename__ = "itinerary_days"
    __table_args__ = (
        UniqueConstraint("travel_plan_id", "day_number", name="uq_itinerary_days_trip_day"),
        UniqueConstraint("travel_plan_id", "calendar_date", name="uq_itinerary_days_trip_date"),
        CheckConstraint("day_number >= 1", name="ck_itinerary_days_day_number"),
        CheckConstraint(
            "daily_budget_estimate IS NULL OR daily_budget_estimate >= 0",
            name="ck_itinerary_days_budget",
        ),
        Index("ix_itinerary_days_travel_plan_id", "travel_plan_id"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    travel_plan_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("travel_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    calendar_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    theme: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    daily_budget_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    travel_plan: Mapped[TravelPlan] = relationship(back_populates="itinerary_days")
    items: Mapped[list["ItineraryItem"]] = relationship(
        back_populates="itinerary_day",
        cascade="all, delete-orphan",
        order_by="ItineraryItem.sort_order",
    )


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"
    __table_args__ = (
        UniqueConstraint("itinerary_day_id", "sort_order", name="uq_itinerary_items_day_sort"),
        CheckConstraint("sort_order >= 1", name="ck_itinerary_items_sort_order"),
        CheckConstraint(
            "item_type IN ('activity', 'meal', 'transport', 'stay', 'note')",
            name="ck_itinerary_items_item_type",
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0",
            name="ck_itinerary_items_duration",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="ck_itinerary_items_estimated_cost",
        ),
        CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR end_time > start_time",
            name="ck_itinerary_items_time_order",
        ),
        Index("ix_itinerary_items_itinerary_day_id", "itinerary_day_id"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    itinerary_day_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("itinerary_days.id", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    booking_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    details: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    itinerary_day: Mapped[ItineraryDay] = relationship(back_populates="items")


class DestinationResearch(Base):
    __tablename__ = "destination_research"
    __table_args__ = (
        UniqueConstraint("trip_id", "source_url", name="uq_destination_research_trip_url"),
        CheckConstraint(
            "content_type IN ('guide', 'attraction', 'itinerary', 'blog', 'map', 'other')",
            name="ck_destination_research_content_type",
        ),
        Index("ix_destination_research_trip_id", "trip_id"),
        Index("ix_destination_research_source_domain", "source_domain"),
        Index("ix_destination_research_scraped_at", "scraped_at"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    trip_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_domain: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    content_type: Mapped[str] = mapped_column(String(24), default="other", nullable=False)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scraped_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    source_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trip: Mapped[Trip] = relationship(back_populates="research_documents")


class MemoryEvent(Base):
    __tablename__ = "memory_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('preference_update', 'behavior_signal', 'trip_generation', 'feedback_learning', 'system_inference')",
            name="ck_memory_events_event_type",
        ),
        CheckConstraint(
            "source IN ('user', 'llm', 'firecrawl', 'system')",
            name="ck_memory_events_source",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_memory_events_confidence_score",
        ),
        Index("ix_memory_events_user_id", "user_id"),
        Index("ix_memory_events_trip_id", "trip_id"),
        Index("ix_memory_events_event_type", "event_type"),
        Index("ix_memory_events_recorded_at", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    trip_id: Mapped[str | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_key: Mapped[str] = mapped_column(String(120), nullable=False)
    event_value: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="memory_events")
    trip: Mapped[Trip | None] = relationship(back_populates="memory_events")


class TripFeedback(Base):
    __tablename__ = "trip_feedback"
    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", name="uq_trip_feedback_trip_user"),
        ForeignKeyConstraint(
            ["trip_id", "user_id"],
            ["trips.id", "trips.user_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_trip_feedback_overall_rating"),
        CheckConstraint("itinerary_rating BETWEEN 1 AND 5", name="ck_trip_feedback_itinerary_rating"),
        CheckConstraint("accuracy_rating BETWEEN 1 AND 5", name="ck_trip_feedback_accuracy_rating"),
        CheckConstraint("value_rating BETWEEN 1 AND 5", name="ck_trip_feedback_value_rating"),
        Index("ix_trip_feedback_trip_id", "trip_id"),
        Index("ix_trip_feedback_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, server_default=text("gen_random_uuid()"))
    trip_id: Mapped[str] = mapped_column(UUID_TYPE, nullable=False)
    user_id: Mapped[str] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    itinerary_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    value_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    liked_points: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    disliked_points: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
        server_default=text("'{}'::text[]"),
        nullable=False,
    )
    would_reuse: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trip: Mapped[Trip] = relationship(
        back_populates="feedback_entries",
        overlaps="feedback_entries,user",
    )
    user: Mapped[User] = relationship(
        back_populates="feedback_entries",
        overlaps="feedback_entries,trip",
    )


Index("uq_users_email_lower", func.lower(User.email), unique=True)
