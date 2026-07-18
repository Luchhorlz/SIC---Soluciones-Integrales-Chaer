"""Create the canonical catalog hierarchy."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260718_0005"
down_revision = "20260718_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("icon_key", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "subcategories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("icon_key", sa.String(80), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_subcategories_category_position", "subcategories", ["category_id", "position"])
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subcategory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(140), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("icon_key", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("allows_fixed_price", sa.Boolean(), nullable=False),
        sa.Column("allows_quote", sa.Boolean(), nullable=False),
        sa.Column("allows_urgent", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["subcategory_id"], ["subcategories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_services_subcategory_name", "services", ["subcategory_id", "name"])


def downgrade() -> None:
    op.drop_index("ix_services_subcategory_name", table_name="services")
    op.drop_table("services")
    op.drop_index("ix_subcategories_category_position", table_name="subcategories")
    op.drop_table("subcategories")
    op.drop_table("categories")
