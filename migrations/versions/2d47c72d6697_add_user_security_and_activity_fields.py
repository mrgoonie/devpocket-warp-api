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


def upgrade() -> None:
    """Add missing security and activity fields to users table."""
    
    # Add subscription fields
    op.add_column('users', sa.Column('subscription_tier', sa.String(length=50), 
                                    nullable=False, server_default="'free'"))
    op.add_column('users', sa.Column('subscription_expires_at', sa.DateTime(timezone=True), 
                                    nullable=True))
    
    # Add security tracking fields
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), 
                                    nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), 
                                    nullable=True))
    
    # Add activity tracking field
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), 
                                    nullable=True))
    
    # Add verification timestamp
    op.add_column('users', sa.Column('verified_at', sa.DateTime(timezone=True), 
                                    nullable=True))


def downgrade() -> None:
    """Remove the security and activity fields from users table."""
    
    # Remove fields in reverse order
    op.drop_column('users', 'verified_at')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'subscription_expires_at')
    op.drop_column('users', 'subscription_tier')