"""create auth and trip memory tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260422_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("home_airport", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("budget_preference", sa.Float(), nullable=True),
        sa.Column("travel_style", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "interests",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("preferred_mood", sa.String(length=24), nullable=False, server_default="relaxed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "trips",
        sa.Column("trip_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column(
            "interests",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("mood", sa.String(length=24), nullable=False),
        sa.Column("highlight", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("best_time_to_visit", sa.Text(), nullable=False),
        sa.Column(
            "live_insights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "attractions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "itinerary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "cost_breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "smart_suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("research_mode", sa.String(length=24), nullable=False, server_default="fallback"),
        sa.Column("research_error", sa.Text(), nullable=True),
        sa.Column(
            "research_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("llm_mode", sa.String(length=24), nullable=False, server_default="fallback"),
        sa.Column("llm_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_id"),
    )
    op.create_index(op.f("ix_trips_destination"), "trips", ["destination"], unique=False)
    op.create_index(op.f("ix_trips_user_id"), "trips", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_trips_user_id"), table_name="trips")
    op.drop_index(op.f("ix_trips_destination"), table_name="trips")
    op.drop_table("trips")
    op.drop_table("user_profiles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
