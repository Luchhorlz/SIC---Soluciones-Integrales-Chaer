"""Create private professional documents and immutable reviews."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260718_0007"
down_revision = "20260718_0006"
branch_labels = None
depends_on = None

media_scan_status = postgresql.ENUM("PENDING", "CLEAN", "INFECTED", "ERROR", name="media_scan_status", create_type=False)
document_status = postgresql.ENUM(
    "DRAFT", "UPLOADED", "SCANNING", "PENDING", "IN_REVIEW", "OBSERVED", "APPROVED", "REJECTED", "EXPIRED", "SUSPENDED",
    name="provider_document_status",
    create_type=False,
)
actor_kind = postgresql.ENUM("REVIEWER", "SYSTEM", name="document_review_actor_kind", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (media_scan_status, document_status, actor_kind):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_bucket", sa.String(120), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("scan_status", media_scan_status, server_default="PENDING", nullable=False),
        sa.Column("scan_message", sa.String(240)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint("owner_user_id", "sha256", name="uq_media_owner_sha256"),
    )
    op.create_index("ix_media_files_owner_user_id", "media_files", ["owner_user_id"])

    op.create_table(
        "service_document_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("jurisdiction_type", sa.String(40), server_default="NONE", nullable=False),
        sa.Column("requires_expiration", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("instructions", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "document_type", name="uq_service_document_requirement"),
    )
    op.create_index("ix_service_document_requirements_service_id", "service_document_requirements", ["service_id"])

    op.create_table(
        "provider_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("document_number", sa.String(120)),
        sa.Column("holder_name", sa.String(180), nullable=False),
        sa.Column("issuer", sa.String(180)),
        sa.Column("jurisdiction", sa.String(180)),
        sa.Column("issued_at", sa.Date()),
        sa.Column("expires_at", sa.Date()),
        sa.Column("media_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", document_status, server_default="UPLOADED", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["media_file_id"], ["media_files.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_file_id"),
    )
    op.create_index("ix_provider_documents_provider_id", "provider_documents", ["provider_id"])
    op.create_index("ix_provider_documents_document_type", "provider_documents", ["document_type"])
    op.create_index("ix_provider_documents_status", "provider_documents", ["status"])

    op.create_table(
        "document_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_kind", actor_kind, server_default="REVIEWER", nullable=False),
        sa.Column("previous_status", document_status, nullable=False),
        sa.Column("new_status", document_status, nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("administrative_context", sa.String(240)),
        sa.Column("audit_reference", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["provider_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_reference"),
    )
    op.create_index("ix_document_reviews_document_id", "document_reviews", ["document_id"])

    # Existing offers were held back only because Phase 5 had no document model.
    # With no requirement configured, documentation is satisfied by definition.
    op.execute("UPDATE provider_services SET status = 'ACTIVE' WHERE status = 'PENDING_DOCUMENTS'")


def downgrade() -> None:
    op.drop_index("ix_document_reviews_document_id", table_name="document_reviews")
    op.drop_table("document_reviews")
    op.drop_index("ix_provider_documents_status", table_name="provider_documents")
    op.drop_index("ix_provider_documents_document_type", table_name="provider_documents")
    op.drop_index("ix_provider_documents_provider_id", table_name="provider_documents")
    op.drop_table("provider_documents")
    op.drop_index("ix_service_document_requirements_service_id", table_name="service_document_requirements")
    op.drop_table("service_document_requirements")
    op.drop_index("ix_media_files_owner_user_id", table_name="media_files")
    op.drop_table("media_files")
    bind = op.get_bind()
    for enum_type in (actor_kind, document_status, media_scan_status):
        enum_type.drop(bind, checkfirst=True)
