"""Create provider profiles, offerings, coverage and availability."""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision = "20260718_0006"
down_revision = "20260718_0005"
branch_labels = None
depends_on = None

profile_status = postgresql.ENUM("DRAFT", "PENDING_REVIEW", "APPROVED", "PAUSED", "SUSPENDED", "BLOCKED", name="provider_profile_status", create_type=False)
subscription_status = postgresql.ENUM("NOT_CONFIGURED", "ACTIVE", "AUTHORIZED", "INACTIVE", name="subscription_visibility_status", create_type=False)
service_status = postgresql.ENUM("DRAFT", "PENDING_DOCUMENTS", "PENDING_REVIEW", "ACTIVE", "PAUSED", "REJECTED", "SUSPENDED", name="provider_service_status", create_type=False)
pricing_type = postgresql.ENUM("FIXED", "FROM", "QUOTE", "HOURLY", "PER_SESSION", "PER_UNIT", name="provider_pricing_type", create_type=False)
modality = postgresql.ENUM("AT_CLIENT_ADDRESS", "REMOTE", "HYBRID", "AT_PROVIDER_LOCATION", "PICKUP_DELIVERY", name="provider_modality", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (profile_status, subscription_status, service_status, pricing_type, modality):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "provider_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("business_name", sa.String(180)),
        sa.Column("bio", sa.Text()),
        sa.Column("experience_years", sa.Integer()),
        sa.Column("base_address_id", postgresql.UUID(as_uuid=True)),
        sa.Column("base_point", Geography(geometry_type="POINT", srid=4326, spatial_index=False)),
        sa.Column("profile_status", profile_status, server_default="DRAFT", nullable=False),
        sa.Column("subscription_visibility_status", subscription_status, server_default="NOT_CONFIGURED", nullable=False),
        sa.Column("rating_average", sa.Numeric(3, 2), server_default="0", nullable=False),
        sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_services_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("response_rate", sa.Float(), server_default="0", nullable=False),
        sa.Column("average_response_minutes", sa.Integer()),
        sa.Column("profile_completeness", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_identity_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["base_address_id"], ["addresses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_provider_profiles_base_point", "provider_profiles", ["base_point"], postgresql_using="gist")

    op.create_table(
        "provider_portfolio_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "position", name="uq_provider_portfolio_position"),
    )
    op.create_index("ix_provider_portfolio_items_provider_id", "provider_portfolio_items", ["provider_id"])

    op.create_table(
        "provider_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", service_status, server_default="PENDING_DOCUMENTS", nullable=False),
        sa.Column("headline", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("pricing_type", pricing_type, nullable=False),
        sa.Column("price_amount", sa.Numeric(12, 2)),
        sa.Column("price_currency", sa.String(3), server_default="ARS", nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer()),
        sa.Column("guarantee_days", sa.Integer()),
        sa.Column("accepts_urgent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("requires_quote_details", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "service_id", name="uq_provider_catalog_service"),
    )
    op.create_index("ix_provider_services_provider_id", "provider_services", ["provider_id"])
    op.create_index("ix_provider_services_service_id", "provider_services", ["service_id"])

    op.create_table(
        "provider_service_modalities",
        sa.Column("provider_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modality", modality, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["provider_service_id"], ["provider_services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("provider_service_id", "modality"),
    )

    op.create_table(
        "provider_service_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("center_address_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("center", Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("radius_meters", sa.Integer(), nullable=False),
        sa.Column("urgent_radius_meters", sa.Integer()),
        sa.Column("travel_fee_policy", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_service_id"], ["provider_services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["center_address_id"], ["addresses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_service_id"),
    )
    op.create_index("ix_provider_service_areas_center", "provider_service_areas", ["center"], postgresql_using="gist")

    op.create_table(
        "availability_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(64), server_default="America/Argentina/Buenos_Aires", nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), server_default="60", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_service_id"], ["provider_services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_service_id", "day_of_week", "start_time", "end_time", name="uq_provider_service_availability_rule"),
    )
    op.create_index("ix_availability_rules_provider_id", "availability_rules", ["provider_id"])
    op.create_index("ix_availability_rules_provider_service_id", "availability_rules", ["provider_service_id"])

    op.create_table(
        "availability_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(240)),
        sa.Column("is_available_override", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_availability_exceptions_provider_id", "availability_exceptions", ["provider_id"])


def downgrade() -> None:
    op.drop_index("ix_availability_exceptions_provider_id", table_name="availability_exceptions")
    op.drop_table("availability_exceptions")
    op.drop_index("ix_availability_rules_provider_service_id", table_name="availability_rules")
    op.drop_index("ix_availability_rules_provider_id", table_name="availability_rules")
    op.drop_table("availability_rules")
    op.drop_index("ix_provider_service_areas_center", table_name="provider_service_areas")
    op.drop_table("provider_service_areas")
    op.drop_table("provider_service_modalities")
    op.drop_index("ix_provider_services_service_id", table_name="provider_services")
    op.drop_index("ix_provider_services_provider_id", table_name="provider_services")
    op.drop_table("provider_services")
    op.drop_index("ix_provider_portfolio_items_provider_id", table_name="provider_portfolio_items")
    op.drop_table("provider_portfolio_items")
    op.drop_index("ix_provider_profiles_base_point", table_name="provider_profiles")
    op.drop_table("provider_profiles")
    bind = op.get_bind()
    for enum_type in (modality, pricing_type, service_status, subscription_status, profile_status):
        enum_type.drop(bind, checkfirst=True)
