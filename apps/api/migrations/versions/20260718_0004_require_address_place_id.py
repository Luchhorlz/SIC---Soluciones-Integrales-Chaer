"""Require a verified Google place id for every address."""
from alembic import op
import sqlalchemy as sa

revision = "20260718_0004"
down_revision = "20260718_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("addresses", "google_place_id", existing_type=sa.String(255), nullable=False)


def downgrade() -> None:
    op.alter_column("addresses", "google_place_id", existing_type=sa.String(255), nullable=True)
