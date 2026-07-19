"""Create configurable plans, provider subscriptions and idempotent billing events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260718_0008"
down_revision = "20260718_0007"
branch_labels = None
depends_on = None

billing_frequency = postgresql.ENUM("MONTHLY", name="billing_frequency", create_type=False)
subscription_provider = postgresql.ENUM("MERCADO_PAGO", name="subscription_provider", create_type=False)
subscription_status = postgresql.ENUM(
    "PENDING", "AUTHORIZED", "ACTIVE", "PAST_DUE", "PAUSED", "CANCELLED", "EXPIRED", "ERROR",
    name="provider_subscription_status",
    create_type=False,
)
billing_processing_status = postgresql.ENUM("RECEIVED", "PROCESSED", "IGNORED", "FAILED", name="billing_processing_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (billing_frequency, subscription_provider, subscription_status, billing_processing_status):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("billing_frequency", billing_frequency, server_default="MONTHLY", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("features_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("mercado_pago_plan_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("uq_subscription_plans_one_active", "subscription_plans", ["is_active"], unique=True, postgresql_where=sa.text("is_active"))

    op.create_table(
        "provider_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_name", subscription_provider, server_default="MERCADO_PAGO", nullable=False),
        sa.Column("external_subscription_id", sa.String(255)),
        sa.Column("status", subscription_status, server_default="PENDING", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_payment_status", sa.String(80)),
        sa.Column("checkout_url", sa.String(2048)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id"),
        sa.UniqueConstraint("external_subscription_id"),
    )
    op.create_index("ix_provider_subscriptions_status", "provider_subscriptions", ["status"])

    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_name", subscription_provider, server_default="MERCADO_PAGO", nullable=False),
        sa.Column("external_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_private_reference", sa.String(255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_status", billing_processing_status, server_default="RECEIVED", nullable=False),
        sa.Column("error_message", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_event_id"),
    )
    op.create_index("ix_billing_events_processing_status", "billing_events", ["processing_status"])


def downgrade() -> None:
    op.drop_index("ix_billing_events_processing_status", table_name="billing_events")
    op.drop_table("billing_events")
    op.drop_index("ix_provider_subscriptions_status", table_name="provider_subscriptions")
    op.drop_table("provider_subscriptions")
    op.drop_index("uq_subscription_plans_one_active", table_name="subscription_plans")
    op.drop_table("subscription_plans")
    bind = op.get_bind()
    for enum_type in (billing_processing_status, subscription_status, subscription_provider, billing_frequency):
        enum_type.drop(bind, checkfirst=True)
