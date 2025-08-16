"""add user security and activity fields

Revision ID: 2d47c72d6697
Revises: 2f441b98e37b
Create Date: 2025-08-16 20:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2d47c72d6697"
down_revision: Union[str, None] = "2f441b98e37b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add missing security and activity fields to users table (idempotent)."""

    # Add subscription fields (only if they don't exist)
    if not column_exists("users", "subscription_tier"):
        op.add_column(
            "users",
            sa.Column(
                "subscription_tier",
                sa.String(length=50),
                nullable=False,
                server_default="'free'",
            ),
        )

    if not column_exists("users", "subscription_expires_at"):
        op.add_column(
            "users",
            sa.Column(
                "subscription_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    # Add security tracking fields (only if they don't exist)
    if not column_exists("users", "failed_login_attempts"):
        op.add_column(
            "users",
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if not column_exists("users", "locked_until"):
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )

    # Add activity tracking field (only if it doesn't exist)
    if not column_exists("users", "last_login_at"):
        op.add_column(
            "users",
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Add verification timestamp (only if it doesn't exist)
    if not column_exists("users", "verified_at"):
        op.add_column(
            "users",
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove the security and activity fields from users table (idempotent)."""

    # Remove fields in reverse order (only if they exist)
    if column_exists("users", "verified_at"):
        op.drop_column("users", "verified_at")

    if column_exists("users", "last_login_at"):
        op.drop_column("users", "last_login_at")

    if column_exists("users", "locked_until"):
        op.drop_column("users", "locked_until")

    if column_exists("users", "failed_login_attempts"):
        op.drop_column("users", "failed_login_attempts")

    if column_exists("users", "subscription_expires_at"):
        op.drop_column("users", "subscription_expires_at")

    if column_exists("users", "subscription_tier"):
        op.drop_column("users", "subscription_tier")
