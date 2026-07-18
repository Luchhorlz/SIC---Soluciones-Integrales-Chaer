"""Enable PostGIS for SIC geospatial data."""
from alembic import op

revision = "20260718_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")


def downgrade() -> None:
    # PostGIS may be shared by future data, so the extension is intentionally preserved.
    pass
