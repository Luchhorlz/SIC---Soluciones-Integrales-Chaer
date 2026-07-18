"""Create private geospatial addresses."""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision = "20260718_0003"
down_revision = "20260718_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("formatted_address", sa.String(500), nullable=False),
        sa.Column("street", sa.String(180), nullable=False),
        sa.Column("street_number", sa.String(30), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("administrative_area", sa.String(120)),
        sa.Column("province", sa.String(120), nullable=False),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("country_code", sa.String(2), server_default="AR", nullable=False),
        sa.Column("google_place_id", sa.String(255)),
        sa.Column("point", Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])
    op.create_index("ix_addresses_point_gist", "addresses", ["point"], postgresql_using="gist")
    op.create_index("uq_addresses_one_default_per_user", "addresses", ["user_id"], unique=True, postgresql_where=sa.text("is_default"))


def downgrade() -> None:
    op.drop_index("uq_addresses_one_default_per_user", table_name="addresses")
    op.drop_index("ix_addresses_point_gist", table_name="addresses")
    op.drop_index("ix_addresses_user_id", table_name="addresses")
    op.drop_table("addresses")
