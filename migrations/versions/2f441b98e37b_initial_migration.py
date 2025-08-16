"""initial_migration

Revision ID: 2f441b98e37b
Revises: 
Create Date: 2025-08-15 16:48:29.622701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = "2f441b98e37b"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists in the database."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
        SELECT 1 FROM pg_type 
        WHERE typname = :enum_name AND typtype = 'e'
    """
        ),
        {"enum_name": enum_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    """
    Handles both fresh installations and upgrades from existing schemas.
    """

    # Create user_role enum if it doesn't exist (completely idempotent)
    bind = op.get_bind()
    try:
        # First check if enum exists, then create if it doesn't
        if not enum_exists("user_role"):
            bind.execute(
                sa.text("CREATE TYPE user_role AS ENUM ('user', 'admin', 'premium')")
            )
    except Exception as e:
        # If enum already exists, this is expected and safe to ignore
        # Log the exception for debugging but continue
        import logging

        logging.warning(
            f"Enum creation warning (likely already exists, safe to ignore): {e}"
        )

        # Double-check that enum actually exists with correct values
        try:
            result = bind.execute(
                sa.text(
                    """
                SELECT enumlabel 
                FROM pg_enum e 
                JOIN pg_type t ON e.enumtypid = t.oid 
                WHERE t.typname = 'user_role' 
                ORDER BY e.enumsortorder
            """
                )
            )
            enum_values = [row[0] for row in result.fetchall()]
            expected_values = ["user", "admin", "premium"]
            if enum_values != expected_values:
                raise Exception(
                    f"Enum 'user_role' exists but has wrong values: {enum_values} (expected {expected_values})"
                )
            logging.info("Enum 'user_role' already exists with correct values")
        except Exception as verify_error:
            logging.error(f"Failed to verify enum values: {verify_error}")
            raise

    # Create or modify users table
    if not table_exists("users"):
        # Fresh install - create users table
        op.create_table(
            "users",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=50), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column(
                "role",
                ENUM("user", "admin", "premium", name="user_role", create_type=False),
                nullable=False,
                server_default="user",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "is_verified", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column("verification_token", sa.String(length=255), nullable=True),
            sa.Column("reset_token", sa.String(length=255), nullable=True),
            sa.Column("reset_token_expires", sa.DateTime(timezone=True), nullable=True),
            sa.Column("openrouter_api_key", sa.String(length=255), nullable=True),
            sa.Column(
                "subscription_tier",
                sa.String(length=50),
                nullable=False,
                server_default="free",
            ),
            sa.Column(
                "subscription_expires_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_created_at", "users", ["created_at"])
        op.create_index("ix_users_updated_at", "users", ["updated_at"])
    else:
        # Upgrade existing users table
        try:
            # Drop old indexes if they exist
            op.drop_index("idx_users_email", table_name="users")
            op.drop_index("idx_users_username", table_name="users")
            op.drop_constraint("users_email_key", "users", type_="unique")
            op.drop_constraint("users_username_key", "users", type_="unique")
        except Exception:
            pass

        # Modify columns
        try:
            op.alter_column("users", "username", type_=sa.String(length=50))
            op.alter_column("users", "created_at", type_=sa.DateTime(timezone=True))
            op.alter_column("users", "updated_at", type_=sa.DateTime(timezone=True))
        except Exception:
            pass

        # Create new indexes
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_id", "users", ["id"])
        op.create_index("ix_users_created_at", "users", ["created_at"])
        op.create_index("ix_users_updated_at", "users", ["updated_at"])

    # Create or modify sessions table
    if not table_exists("sessions"):
        # Fresh install - create sessions table
        op.create_table(
            "sessions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("device_id", sa.String(length=255), nullable=False),
            sa.Column("device_type", sa.String(length=20), nullable=False),
            sa.Column("device_name", sa.String(length=100), nullable=True),
            sa.Column("session_name", sa.String(length=100), nullable=True),
            sa.Column(
                "session_type",
                sa.String(length=20),
                nullable=False,
                server_default="terminal",
            ),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ssh_host", sa.String(length=255), nullable=True),
            sa.Column("ssh_port", sa.Integer(), nullable=True),
            sa.Column("ssh_username", sa.String(length=100), nullable=True),
            sa.Column(
                "terminal_cols", sa.Integer(), nullable=False, server_default="80"
            ),
            sa.Column(
                "terminal_rows", sa.Integer(), nullable=False, server_default="24"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_sessions_id", "sessions", ["id"])
        op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
        op.create_index("ix_sessions_device_id", "sessions", ["device_id"])
        op.create_index("ix_sessions_device_type", "sessions", ["device_type"])
        op.create_index("ix_sessions_is_active", "sessions", ["is_active"])
        op.create_index("ix_sessions_created_at", "sessions", ["created_at"])
        op.create_index("ix_sessions_updated_at", "sessions", ["updated_at"])
        op.create_index(
            "ix_sessions_last_activity_at", "sessions", ["last_activity_at"]
        )
    else:
        # Upgrade existing sessions table
        try:
            # Drop old columns and indexes
            op.drop_index("idx_sessions_token_hash", table_name="sessions")
            op.drop_index("idx_sessions_user_id", table_name="sessions")
            op.drop_constraint("sessions_token_hash_key", "sessions", type_="unique")
            op.drop_column("sessions", "token_hash")
            op.drop_column("sessions", "expires_at")
            op.drop_column("sessions", "device_info")
            op.drop_column("sessions", "last_activity")
        except Exception:
            pass

        # Add new columns
        try:
            op.add_column(
                "sessions",
                sa.Column("device_id", sa.String(length=255), nullable=False),
            )
            op.add_column(
                "sessions",
                sa.Column("device_type", sa.String(length=20), nullable=False),
            )
            op.add_column(
                "sessions",
                sa.Column("device_name", sa.String(length=100), nullable=True),
            )
            op.add_column(
                "sessions",
                sa.Column("session_name", sa.String(length=100), nullable=True),
            )
            op.add_column(
                "sessions",
                sa.Column(
                    "session_type",
                    sa.String(length=20),
                    nullable=False,
                    server_default="terminal",
                ),
            )
            op.add_column("sessions", sa.Column("user_agent", sa.Text(), nullable=True))
            op.add_column(
                "sessions",
                sa.Column(
                    "is_active", sa.Boolean(), nullable=False, server_default="true"
                ),
            )
            op.add_column(
                "sessions",
                sa.Column(
                    "last_activity_at", sa.DateTime(timezone=True), nullable=True
                ),
            )
            op.add_column(
                "sessions",
                sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            )
            op.add_column(
                "sessions", sa.Column("ssh_host", sa.String(length=255), nullable=True)
            )
            op.add_column(
                "sessions", sa.Column("ssh_port", sa.Integer(), nullable=True)
            )
            op.add_column(
                "sessions",
                sa.Column("ssh_username", sa.String(length=100), nullable=True),
            )
            op.add_column(
                "sessions",
                sa.Column(
                    "terminal_cols", sa.Integer(), nullable=False, server_default="80"
                ),
            )
            op.add_column(
                "sessions",
                sa.Column(
                    "terminal_rows", sa.Integer(), nullable=False, server_default="24"
                ),
            )
            op.add_column(
                "sessions",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )
        except Exception:
            pass

        # Modify existing columns
        try:
            op.alter_column("sessions", "ip_address", type_=sa.String(length=45))
            op.alter_column("sessions", "created_at", type_=sa.DateTime(timezone=True))
        except Exception:
            pass

        # Create new indexes
        try:
            op.create_index("ix_sessions_id", "sessions", ["id"])
            op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
            op.create_index("ix_sessions_device_id", "sessions", ["device_id"])
            op.create_index("ix_sessions_device_type", "sessions", ["device_type"])
            op.create_index("ix_sessions_is_active", "sessions", ["is_active"])
            op.create_index("ix_sessions_created_at", "sessions", ["created_at"])
            op.create_index("ix_sessions_updated_at", "sessions", ["updated_at"])
            op.create_index(
                "ix_sessions_last_activity_at", "sessions", ["last_activity_at"]
            )
        except Exception:
            pass

    # Drop old tables if they exist
    # Using raw SQL with IF EXISTS to avoid transaction abortion
    bind = op.get_bind()
    for table_name in ["workflows", "sync_queue", "command_history", "ssh_connections"]:
        try:
            bind.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        except Exception:
            pass

    # Create ssh_keys table
    op.create_table(
        "ssh_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("key_type", sa.String(length=20), nullable=False),
        sa.Column("key_size", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(length=200), nullable=False),
        sa.Column("encrypted_private_key", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("comment", sa.String(length=255), nullable=True),
        sa.Column(
            "has_passphrase", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssh_keys_id", "ssh_keys", ["id"])
    op.create_index("ix_ssh_keys_user_id", "ssh_keys", ["user_id"])
    op.create_index("ix_ssh_keys_fingerprint", "ssh_keys", ["fingerprint"], unique=True)
    op.create_index("ix_ssh_keys_created_at", "ssh_keys", ["created_at"])
    op.create_index("ix_ssh_keys_updated_at", "ssh_keys", ["updated_at"])

    # Create user_settings table
    op.create_table(
        "user_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "terminal_theme",
            sa.String(length=50),
            nullable=False,
            server_default="dark",
        ),
        sa.Column(
            "terminal_font_size", sa.Integer(), nullable=False, server_default="14"
        ),
        sa.Column(
            "terminal_font_family",
            sa.String(length=50),
            nullable=False,
            server_default="Fira Code",
        ),
        sa.Column(
            "preferred_ai_model",
            sa.String(length=100),
            nullable=False,
            server_default="claude-3-haiku",
        ),
        sa.Column(
            "ai_suggestions_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "ai_explanations_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("sync_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sync_commands", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "sync_ssh_profiles", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("custom_settings", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_settings_id", "user_settings", ["id"])
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"])
    op.create_index("ix_user_settings_created_at", "user_settings", ["created_at"])
    op.create_index("ix_user_settings_updated_at", "user_settings", ["updated_at"])

    # Create sync_data table
    op.create_table(
        "sync_data",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("sync_type", sa.String(length=50), nullable=False),
        sa.Column("sync_key", sa.String(length=255), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source_device_id", sa.String(length=255), nullable=False),
        sa.Column("source_device_type", sa.String(length=20), nullable=False),
        sa.Column("conflict_data", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
        ),
        sa.Column(
            "last_modified_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_data_id", "sync_data", ["id"])
    op.create_index("ix_sync_data_user_id", "sync_data", ["user_id"])
    op.create_index("ix_sync_data_sync_type", "sync_data", ["sync_type"])
    op.create_index("ix_sync_data_sync_key", "sync_data", ["sync_key"])
    op.create_index("ix_sync_data_is_deleted", "sync_data", ["is_deleted"])
    op.create_index("ix_sync_data_synced_at", "sync_data", ["synced_at"])
    op.create_index("ix_sync_data_created_at", "sync_data", ["created_at"])
    op.create_index("ix_sync_data_updated_at", "sync_data", ["updated_at"])

    # Create commands table
    op.create_table(
        "commands",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("error_output", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time", sa.Float(), nullable=True),
        sa.Column("working_directory", sa.String(length=500), nullable=True),
        sa.Column("environment_vars", sa.Text(), nullable=True),
        sa.Column(
            "was_ai_suggested", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("command_type", sa.String(length=50), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commands_id", "commands", ["id"])
    op.create_index("ix_commands_session_id", "commands", ["session_id"])
    op.create_index("ix_commands_command", "commands", ["command"])
    op.create_index("ix_commands_status", "commands", ["status"])
    op.create_index("ix_commands_exit_code", "commands", ["exit_code"])
    op.create_index("ix_commands_command_type", "commands", ["command_type"])
    op.create_index("ix_commands_was_ai_suggested", "commands", ["was_ai_suggested"])
    op.create_index("ix_commands_created_at", "commands", ["created_at"])
    op.create_index("ix_commands_updated_at", "commands", ["updated_at"])

    # Create composite indexes for better performance
    op.create_index(
        "idx_commands_session_created", "commands", ["session_id", "created_at"]
    )
    op.create_index("idx_commands_status_created", "commands", ["status", "created_at"])
    op.create_index(
        "idx_commands_ai_suggested", "commands", ["was_ai_suggested", "created_at"]
    )
    op.create_index("idx_commands_user_command", "commands", ["session_id", "command"])

    # Create ssh_profiles table
    op.create_table(
        "ssh_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column(
            "auth_method", sa.String(length=20), nullable=False, server_default="key"
        ),
        sa.Column("ssh_key_id", sa.UUID(), nullable=True),
        sa.Column("compression", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "strict_host_key_checking",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "connection_timeout", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("ssh_options", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "successful_connections", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "failed_connections", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ssh_key_id"], ["ssh_keys.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssh_profiles_id", "ssh_profiles", ["id"])
    op.create_index("ix_ssh_profiles_user_id", "ssh_profiles", ["user_id"])
    op.create_index("ix_ssh_profiles_ssh_key_id", "ssh_profiles", ["ssh_key_id"])
    op.create_index("ix_ssh_profiles_created_at", "ssh_profiles", ["created_at"])
    op.create_index("ix_ssh_profiles_updated_at", "ssh_profiles", ["updated_at"])


def downgrade() -> None:
    """Reverse the migration."""
    # Drop tables in reverse order of dependencies using IF EXISTS to avoid errors
    bind = op.get_bind()
    tables = [
        "ssh_profiles",
        "commands",
        "sync_data",
        "user_settings",
        "ssh_keys",
        "sessions",
        "users",
    ]

    for table_name in tables:
        try:
            bind.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
        except Exception:
            pass

    # Drop enum type (only if no tables are using it)
    try:
        bind = op.get_bind()
        # Check if any tables are still using the enum type
        result = bind.execute(
            sa.text(
                """
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE udt_name = 'user_role'
        """
            )
        )
        if result.fetchone()[0] == 0:
            bind.execute(sa.text("DROP TYPE IF EXISTS user_role"))
    except Exception as e:
        # Safe to ignore - enum might be in use by other tables
        import logging

        logging.warning(f"Enum drop warning (safe to ignore): {e}")
        pass
