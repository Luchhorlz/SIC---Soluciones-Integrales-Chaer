"""Create users and roles."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260718_0002"
down_revision = "20260718_0001"
branch_labels = None
depends_on = None

user_status = postgresql.ENUM("ACTIVE", "SUSPENDED", "BLOCKED", "DELETED", name="user_status", create_type=False)
user_role_name = postgresql.ENUM("CLIENT", "PROVIDER", "ADMIN", "DOCUMENT_REVIEWER", "SUPPORT", name="user_role_name", create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    user_status.create(op.get_bind(), checkfirst=True)
    user_role_name.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("google_subject", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("avatar_url", sa.String(2048)),
        sa.Column("phone", sa.String(40)),
        sa.Column("status", user_status, server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_subject"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role_name, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role"),
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("users")
    user_role_name.drop(op.get_bind(), checkfirst=True)
    user_status.drop(op.get_bind(), checkfirst=True)
