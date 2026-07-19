"""Mark development-only demo identities and provider profiles."""

from alembic import op
import sqlalchemy as sa


revision = "20260719_0011"
down_revision = "20260719_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_users_is_demo", "users", ["is_demo"])
    op.add_column("provider_profiles", sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_provider_profiles_is_demo", "provider_profiles", ["is_demo"])


def downgrade() -> None:
    op.drop_index("ix_provider_profiles_is_demo", table_name="provider_profiles")
    op.drop_column("provider_profiles", "is_demo")
    op.drop_index("ix_users_is_demo", table_name="users")
    op.drop_column("users", "is_demo")
