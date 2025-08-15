"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-08-15 15:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_role enum
    user_role_enum = postgresql.ENUM('user', 'admin', 'premium', name='user_role')
    user_role_enum.create(op.get_bind())
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', user_role_enum, nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('openrouter_api_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_updated_at'), 'users', ['updated_at'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)

    # Create user_settings table
    op.create_table('user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('terminal_theme', sa.String(length=50), nullable=False, server_default='dark'),
        sa.Column('terminal_font_size', sa.Integer(), nullable=False, server_default='14'),
        sa.Column('terminal_font_family', sa.String(length=50), nullable=False, server_default='Fira Code'),
        sa.Column('preferred_ai_model', sa.String(length=100), nullable=False, server_default='claude-3-haiku'),
        sa.Column('ai_suggestions_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ai_explanations_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_commands', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_ssh_profiles', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('custom_settings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_settings_created_at'), 'user_settings', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_settings_id'), 'user_settings', ['id'], unique=False)
    op.create_index(op.f('ix_user_settings_updated_at'), 'user_settings', ['updated_at'], unique=False)
    op.create_index(op.f('ix_user_settings_user_id'), 'user_settings', ['user_id'], unique=False)

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('session_name', sa.String(length=100), nullable=True),
        sa.Column('session_type', sa.String(length=20), nullable=False, server_default='terminal'),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('device_type', sa.String(length=20), nullable=True),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ssh_host', sa.String(length=255), nullable=True),
        sa.Column('ssh_port', sa.Integer(), nullable=True),
        sa.Column('ssh_username', sa.String(length=100), nullable=True),
        sa.Column('terminal_cols', sa.Integer(), nullable=True),
        sa.Column('terminal_rows', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_created_at'), 'sessions', ['created_at'], unique=False)
    op.create_index(op.f('ix_sessions_device_id'), 'sessions', ['device_id'], unique=False)
    op.create_index(op.f('ix_sessions_device_type'), 'sessions', ['device_type'], unique=False)
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)
    op.create_index(op.f('ix_sessions_is_active'), 'sessions', ['is_active'], unique=False)
    op.create_index(op.f('ix_sessions_last_activity_at'), 'sessions', ['last_activity_at'], unique=False)
    op.create_index(op.f('ix_sessions_updated_at'), 'sessions', ['updated_at'], unique=False)
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)

    # Create ssh_keys table
    op.create_table('ssh_keys',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('key_type', sa.String(length=20), nullable=False),
        sa.Column('key_size', sa.Integer(), nullable=True),
        sa.Column('fingerprint', sa.String(length=200), nullable=False),
        sa.Column('encrypted_private_key', sa.LargeBinary(), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('comment', sa.String(length=255), nullable=True),
        sa.Column('has_passphrase', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ssh_keys_created_at'), 'ssh_keys', ['created_at'], unique=False)
    op.create_index(op.f('ix_ssh_keys_fingerprint'), 'ssh_keys', ['fingerprint'], unique=False)
    op.create_index(op.f('ix_ssh_keys_id'), 'ssh_keys', ['id'], unique=False)
    op.create_index(op.f('ix_ssh_keys_updated_at'), 'ssh_keys', ['updated_at'], unique=False)
    op.create_index(op.f('ix_ssh_keys_user_id'), 'ssh_keys', ['user_id'], unique=False)

    # Create ssh_profiles table
    op.create_table('ssh_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='22'),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('auth_method', sa.String(length=20), nullable=False, server_default='password'),
        sa.Column('password', sa.String(length=255), nullable=True),
        sa.Column('ssh_key_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['ssh_key_id'], ['ssh_keys.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ssh_profiles_created_at'), 'ssh_profiles', ['created_at'], unique=False)
    op.create_index(op.f('ix_ssh_profiles_id'), 'ssh_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_ssh_profiles_ssh_key_id'), 'ssh_profiles', ['ssh_key_id'], unique=False)
    op.create_index(op.f('ix_ssh_profiles_updated_at'), 'ssh_profiles', ['updated_at'], unique=False)
    op.create_index(op.f('ix_ssh_profiles_user_id'), 'ssh_profiles', ['user_id'], unique=False)

    # Create commands table
    op.create_table('commands',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('error_output', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('working_directory', sa.String(length=500), nullable=True),
        sa.Column('environment_vars', sa.Text(), nullable=True),
        sa.Column('was_ai_suggested', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ai_explanation', sa.Text(), nullable=True),
        sa.Column('command_type', sa.String(length=50), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_commands_ai_suggested', 'commands', ['was_ai_suggested', 'created_at'], unique=False)
    op.create_index('idx_commands_session_created', 'commands', ['session_id', 'created_at'], unique=False)
    op.create_index('idx_commands_status_created', 'commands', ['status', 'created_at'], unique=False)
    op.create_index('idx_commands_user_command', 'commands', ['session_id', 'command'], unique=False)
    op.create_index(op.f('ix_commands_command'), 'commands', ['command'], unique=False)
    op.create_index(op.f('ix_commands_command_type'), 'commands', ['command_type'], unique=False)
    op.create_index(op.f('ix_commands_created_at'), 'commands', ['created_at'], unique=False)
    op.create_index(op.f('ix_commands_exit_code'), 'commands', ['exit_code'], unique=False)
    op.create_index(op.f('ix_commands_id'), 'commands', ['id'], unique=False)
    op.create_index(op.f('ix_commands_session_id'), 'commands', ['session_id'], unique=False)
    op.create_index(op.f('ix_commands_status'), 'commands', ['status'], unique=False)
    op.create_index(op.f('ix_commands_updated_at'), 'commands', ['updated_at'], unique=False)
    op.create_index(op.f('ix_commands_was_ai_suggested'), 'commands', ['was_ai_suggested'], unique=False)

    # Create sync_data table
    op.create_table('sync_data',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('sync_key', sa.String(length=200), nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),
        sa.Column('data_content', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('client_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'sync_key', name='uq_sync_data_user_key')
    )
    op.create_index(op.f('ix_sync_data_created_at'), 'sync_data', ['created_at'], unique=False)
    op.create_index(op.f('ix_sync_data_id'), 'sync_data', ['id'], unique=False)
    op.create_index(op.f('ix_sync_data_is_deleted'), 'sync_data', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_sync_data_sync_key'), 'sync_data', ['sync_key'], unique=False)
    op.create_index(op.f('ix_sync_data_sync_type'), 'sync_data', ['sync_type'], unique=False)
    op.create_index(op.f('ix_sync_data_synced_at'), 'sync_data', ['synced_at'], unique=False)
    op.create_index(op.f('ix_sync_data_updated_at'), 'sync_data', ['updated_at'], unique=False)
    op.create_index(op.f('ix_sync_data_user_id'), 'sync_data', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('sync_data')
    op.drop_table('commands')
    op.drop_table('ssh_profiles')
    op.drop_table('ssh_keys')
    op.drop_table('sessions')
    op.drop_table('user_settings')
    op.drop_table('users')
    
    # Drop enum
    user_role_enum = postgresql.ENUM('user', 'admin', 'premium', name='user_role')
    user_role_enum.drop(op.get_bind())