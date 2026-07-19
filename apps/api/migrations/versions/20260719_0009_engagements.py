"""Create private requests, quotes, attachments and bookings."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260719_0009"
down_revision = "20260718_0008"
branch_labels = None
depends_on = None

request_status = postgresql.ENUM("DRAFT", "REQUESTED", "VIEWED", "QUOTED", "ACCEPTED", "DECLINED", "CANCELLED", "EXPIRED", "CONVERTED_TO_BOOKING", name="service_request_status", create_type=False)
quote_status = postgresql.ENUM("SENT", "ACCEPTED", "REJECTED", "EXPIRED", "WITHDRAWN", name="quote_status", create_type=False)
booking_status = postgresql.ENUM("PENDING_PROVIDER", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED_BY_CLIENT", "CANCELLED_BY_PROVIDER", "NO_SHOW", "DISPUTED", name="booking_status", create_type=False)
modality = postgresql.ENUM("AT_CLIENT_ADDRESS", "REMOTE", "HYBRID", "AT_PROVIDER_LOCATION", "PICKUP_DELIVERY", name="provider_modality", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (request_status, quote_status, booking_status):
        enum_type.create(bind, checkfirst=True)
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "service_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_address_id", postgresql.UUID(as_uuid=True)),
        sa.Column("selected_modality", modality, nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("preferred_start_at", sa.DateTime(timezone=True)),
        sa.Column("status", request_status, server_default="REQUESTED", nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_service_id"], ["provider_services.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_address_id"], ["addresses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_requests_client_status", "service_requests", ["client_id", "status", "created_at"])
    op.create_index("ix_service_requests_provider_status", "service_requests", ["provider_id", "status", "created_at"])

    op.create_table(
        "request_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_file_id"], ["media_files.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_file_id", name="uq_request_attachment_media"),
    )
    op.create_index("ix_request_attachments_request_id", "request_attachments", ["request_id"])

    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="ARS", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", quote_status, server_default="SENT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_quote_amount_positive"),
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotes_request_status", "quotes", ["request_id", "status", "created_at"])

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("modality", modality, nullable=False),
        sa.Column("address_snapshot_encrypted", sa.Text()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agreed_price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), server_default="ARS", nullable=False),
        sa.Column("status", booking_status, server_default="CONFIRMED", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("client_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("dispute_reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_booking_valid_schedule"),
        sa.CheckConstraint("agreed_price IS NULL OR agreed_price > 0", name="ck_booking_price_positive"),
        sa.ForeignKeyConstraint(["request_id"], ["service_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_service_id"], ["provider_services.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_booking_request"),
    )
    op.create_index("ix_bookings_client_status", "bookings", ["client_id", "status", "starts_at"])
    op.create_index("ix_bookings_provider_status", "bookings", ["provider_id", "status", "starts_at"])
    op.execute("ALTER TABLE bookings ADD CONSTRAINT ex_bookings_provider_schedule EXCLUDE USING gist (provider_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status IN ('CONFIRMED', 'IN_PROGRESS'))")


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("quotes")
    op.drop_table("request_attachments")
    op.drop_table("service_requests")
    bind = op.get_bind()
    for enum_type in (booking_status, quote_status, request_status):
        enum_type.drop(bind, checkfirst=True)
