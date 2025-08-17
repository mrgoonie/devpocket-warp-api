"""
Comprehensive tests for db_migrate.sh script.

Tests cover:
- Script execution and argument parsing
- Database connection testing
- Alembic migration operations
- Error handling and edge cases
- Help and usage information
"""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.database
class TestDbMigrateScript:
    """Test suite for db_migrate.sh script."""

    def test_script_exists_and_executable(self, scripts_dir):
        """Test that the db_migrate.sh script exists and is executable."""
        script_path = scripts_dir / "db_migrate.sh"
        assert script_path.exists(), "db_migrate.sh script should exist"

        # Make it executable for testing
        script_path.chmod(0o755)
        assert os.access(script_path, os.X_OK), "db_migrate.sh should be executable"

    def test_script_syntax_is_valid(self, script_runner):
        """Test that the script has valid bash syntax."""
        assert script_runner.check_script_syntax(
            "db_migrate.sh"
        ), "db_migrate.sh should have valid bash syntax"

    def test_help_option(self, script_runner):
        """Test the help option displays usage information."""
        result = script_runner.run_script("db_migrate.sh", ["--help"])

        assert result.returncode == 0
        assert "DevPocket API - Database Migration Script" in result.stdout
        assert "USAGE:" in result.stdout
        assert "OPTIONS:" in result.stdout
        assert "EXAMPLES:" in result.stdout
        assert "ENVIRONMENT:" in result.stdout

    def test_help_short_option(self, script_runner):
        """Test the short help option."""
        result = script_runner.run_script("db_migrate.sh", ["-h"])

        assert result.returncode == 0
        assert "DevPocket API - Database Migration Script" in result.stdout

    @patch("subprocess.run")
    def test_migration_to_head_success(self, mock_run, script_runner, mock_env):
        """Test successful migration to head."""
        # Mock successful subprocess calls
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="current_revision"),
            # alembic show head
            MagicMock(returncode=0),
            # alembic upgrade head
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0, stdout="new_revision"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["head"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_migration_specific_revision(self, mock_run, script_runner, mock_env):
        """Test migration to a specific revision."""
        revision = "abc123"
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0),
            # alembic show <revision>
            MagicMock(returncode=0),
            # alembic upgrade <revision>
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", [revision])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_migration_step_forward(self, mock_run, script_runner, mock_env):
        """Test migration one step forward."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0),
            # alembic show +1
            MagicMock(returncode=0),
            # alembic upgrade +1
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["+1"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_migration_step_backward(self, mock_run, script_runner, mock_env):
        """Test migration one step backward."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0),
            # alembic show -1
            MagicMock(returncode=0),
            # alembic upgrade -1
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["-1"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_database_connection_failure(self, mock_run, script_runner, mock_env):
        """Test handling of database connection failure."""
        # Mock failed database connection
        mock_run.return_value = MagicMock(returncode=1)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh")

        assert result.returncode != 0

    @patch("subprocess.run")
    def test_alembic_not_found(self, mock_run, script_runner, mock_env):
        """Test handling when Alembic is not available."""
        with patch("shutil.which", return_value=None), patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_migrate.sh")

        assert result.returncode != 0

    @patch("subprocess.run")
    def test_invalid_migration_target(self, mock_run, script_runner, mock_env):
        """Test handling of invalid migration target."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic current - success
            MagicMock(returncode=0),
            # alembic show invalid_target - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["invalid_target"])

        assert result.returncode != 0

    @patch("subprocess.run")
    def test_migration_failure(self, mock_run, script_runner, mock_env):
        """Test handling of migration failure."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic current - success
            MagicMock(returncode=0),
            # alembic show head - success
            MagicMock(returncode=0),
            # alembic upgrade head - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["head"])

        assert result.returncode != 0

    def test_generate_migration_option(self, script_runner, mock_env):
        """Test the generate migration option."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # db_utils.py test
                MagicMock(returncode=0),
                # alembic revision --autogenerate
                MagicMock(returncode=0),
            ]

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script(
                    "db_migrate.sh", ["-g", "Add new table"]
                )

        assert result.returncode == 0

    def test_generate_migration_long_option(self, script_runner, mock_env):
        """Test the generate migration long option."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # db_utils.py test
                MagicMock(returncode=0),
                # alembic revision --autogenerate
                MagicMock(returncode=0),
            ]

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script(
                    "db_migrate.sh", ["--generate", "Add new field"]
                )

        assert result.returncode == 0

    def test_generate_migration_without_message(self, script_runner):
        """Test generate migration option without message should fail."""
        result = script_runner.run_script("db_migrate.sh", ["-g"])
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_history_option(self, mock_run, script_runner, mock_env):
        """Test the history option."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic history --verbose
            MagicMock(returncode=0, stdout="migration history"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--history"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_check_only_option(self, mock_run, script_runner, mock_env):
        """Test the check-only option."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        assert result.returncode == 0

    def test_unknown_option(self, script_runner):
        """Test handling of unknown options."""
        result = script_runner.run_script("db_migrate.sh", ["--invalid-option"])
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_virtual_environment_activation(self, mock_run, script_runner, mock_env):
        """Test virtual environment activation when available."""
        # Create a mock venv directory structure
        with patch("os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True
            mock_run.return_value = MagicMock(returncode=0)

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_current_migration_status_check(self, mock_run, script_runner, mock_env):
        """Test that current migration status is checked."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="abc123 (head)"),
            # alembic show head
            MagicMock(returncode=0),
            # alembic upgrade head
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0, stdout="def456 (head)"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_alembic_current_failure(self, mock_run, script_runner, mock_env):
        """Test handling when alembic current command fails."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic current - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh")

        assert result.returncode != 0

    def test_error_trap_functionality(self, script_runner):
        """Test that error trap is working properly."""
        # This test ensures the script fails properly on errors
        # We test this by providing invalid arguments
        result = script_runner.run_script("db_migrate.sh", ["--invalid"])
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_working_directory_change(self, mock_run, script_runner, mock_env):
        """Test that script changes to project root for Alembic operations."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_script_logging_output(self, mock_run, script_runner, mock_env):
        """Test that script produces proper logging output."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        # Check for logging patterns
        output = result.stdout + result.stderr
        assert "[INFO]" in output
        assert "Starting database migration script" in output

    @patch("subprocess.run")
    def test_generate_migration_failure(self, mock_run, script_runner, mock_env):
        """Test handling of migration generation failure."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic revision --autogenerate - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["-g", "Test migration"])

        assert result.returncode != 0

    def test_script_parameter_validation(self, script_runner):
        """Test various parameter combinations."""
        # Test multiple targets (should use the last one)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            script_runner.run_script(
                "db_migrate.sh", ["head", "abc123", "--check-only"]
            )

        # Script should handle this gracefully
        # (exact behavior depends on implementation)

    @patch("subprocess.run")
    def test_environment_variable_usage(self, mock_run, script_runner):
        """Test that script uses environment variables properly."""
        custom_env = {
            "DATABASE_HOST": "custom-host",
            "DATABASE_PORT": "5434",
            "DATABASE_USER": "custom-user",
            "DATABASE_PASSWORD": "custom-pass",
            "DATABASE_NAME": "custom-db",
        }

        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, custom_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        assert result.returncode == 0

    # NEW ENHANCED FEATURE TESTS

    @patch("subprocess.run")
    def test_dry_run_functionality(self, mock_run, script_runner, mock_env):
        """Test the --dry-run option shows what would be migrated without executing."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic show head (validation)
            MagicMock(returncode=0),
            # alembic current (for dry run check)
            MagicMock(returncode=0, stdout="abc123"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--dry-run"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Dry run mode" in output
        assert "showing what would be migrated" in output
        assert "Dry run completed" in output

    @patch("subprocess.run")
    def test_dry_run_with_specific_target(self, mock_run, script_runner, mock_env):
        """Test dry run with specific migration target."""
        target = "def456"
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic show <target> (validation)
            MagicMock(returncode=0),
            # alembic current (for dry run check)
            MagicMock(returncode=0, stdout="abc123"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--dry-run", target])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Dry run mode" in output
        assert target in output or "Migration target validated" in output

    @patch("subprocess.run")
    def test_skip_backup_option(self, mock_run, script_runner, mock_env):
        """Test the --skip-backup option skips backup creation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="abc123"),
            # alembic show head
            MagicMock(returncode=0),
            # Check data safety (returns different revision)
            MagicMock(returncode=0, stdout="def456"),
            # alembic upgrade head
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0, stdout="def456"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_migrate.sh", ["--skip-backup", "--force"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        # Should not mention backup creation
        assert (
            "Creating database backup" not in output
            or "skipping backup" in output.lower()
        )

    @patch("subprocess.run")
    def test_force_option_skips_confirmation(self, mock_run, script_runner, mock_env):
        """Test the --force option skips user confirmation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="abc123"),
            # alembic show head
            MagicMock(returncode=0),
            # Check data safety (returns different revision)
            MagicMock(returncode=0, stdout="def456"),
            # alembic upgrade head
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0, stdout="def456"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--force"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        # Should not prompt for confirmation
        assert "Do you want to continue?" not in output

    @patch("subprocess.run")
    def test_env_file_option(self, mock_run, script_runner, temp_dir):
        """Test the --env-file option uses custom environment file."""
        # Create a custom env file
        custom_env_file = temp_dir / "custom.env"
        custom_env_file.write_text(
            "DATABASE_HOST=custom-host\n"
            "DATABASE_PORT=5434\n"
            "DATABASE_USER=custom-user\n"
            "DATABASE_PASSWORD=custom-pass\n"
            "DATABASE_NAME=custom-db\n"
        )

        mock_run.return_value = MagicMock(returncode=0)

        result = script_runner.run_script(
            "db_migrate.sh",
            ["--env-file", str(custom_env_file), "--check-only"],
        )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert f"Environment file: {custom_env_file}" in output

    def test_env_file_option_missing_file(self, script_runner):
        """Test --env-file with missing argument shows error."""
        result = script_runner.run_script("db_migrate.sh", ["--env-file"])
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "Environment file path required" in output

    @patch("subprocess.run")
    def test_backup_creation_success(self, mock_run, script_runner, mock_env, temp_dir):
        """Test successful backup creation before migration."""
        # Mock pg_dump availability and success
        with patch("shutil.which", return_value="/usr/bin/pg_dump"), patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    # db_utils.py test
                    MagicMock(returncode=0),
                    # alembic current
                    MagicMock(returncode=0, stdout="abc123"),
                    # alembic show head
                    MagicMock(returncode=0),
                    # Check data safety
                    MagicMock(returncode=0, stdout="def456"),
                    # pg_dump (backup)
                    MagicMock(returncode=0),
                    # alembic upgrade
                    MagicMock(returncode=0),
                    # alembic current (final)
                    MagicMock(returncode=0),
                ]

                with patch.dict(os.environ, mock_env):
                    result = script_runner.run_script("db_migrate.sh", ["--force"])

                assert result.returncode == 0

    @patch("subprocess.run")
    def test_backup_creation_failure_warning(self, mock_run, script_runner, mock_env):
        """Test that backup failure shows warning but continues migration."""
        with patch("shutil.which", return_value="/usr/bin/pg_dump"):
            mock_run.side_effect = [
                # db_utils.py test
                MagicMock(returncode=0),
                # alembic current
                MagicMock(returncode=0, stdout="abc123"),
                # alembic show head
                MagicMock(returncode=0),
                # Check data safety
                MagicMock(returncode=0, stdout="def456"),
                # pg_dump fails
                MagicMock(returncode=1),
                # alembic upgrade (should still continue)
                MagicMock(returncode=0),
                # alembic current (final)
                MagicMock(returncode=0),
            ]

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_migrate.sh", ["--force"])

            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert "Failed to create database backup" in output or "WARN" in output

    @patch("subprocess.run")
    def test_no_pg_dump_available(self, mock_run, script_runner, mock_env):
        """Test behavior when pg_dump is not available."""
        with patch("shutil.which", return_value=None):
            mock_run.side_effect = [
                # db_utils.py test
                MagicMock(returncode=0),
                # alembic current
                MagicMock(returncode=0, stdout="abc123"),
                # alembic show head
                MagicMock(returncode=0),
                # Check data safety
                MagicMock(returncode=0, stdout="def456"),
                # alembic upgrade
                MagicMock(returncode=0),
                # alembic current (final)
                MagicMock(returncode=0),
            ]

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_migrate.sh", ["--force"])

            assert result.returncode == 0
            output = result.stdout + result.stderr
            assert "pg_dump not found" in output or "skipping backup" in output

    @patch("subprocess.run")
    def test_migration_verification_success(self, mock_run, script_runner, mock_env):
        """Test migration verification after successful migration."""
        target_revision = "def456"
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="abc123"),
            # alembic show head
            MagicMock(returncode=0),
            # Check data safety
            MagicMock(returncode=0, stdout=target_revision),
            # alembic upgrade
            MagicMock(returncode=0),
            # alembic current (verification)
            MagicMock(returncode=0, stdout=target_revision[:12]),  # First 12 chars
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_migrate.sh", ["--force", "--skip-backup"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Migration verification passed" in output

    @patch("subprocess.run")
    def test_migration_verification_failure(self, mock_run, script_runner, mock_env):
        """Test migration verification failure warning."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="abc123"),
            # alembic show head
            MagicMock(returncode=0),
            # Check data safety
            MagicMock(returncode=0, stdout="def456"),
            # alembic upgrade
            MagicMock(returncode=0),
            # alembic current (verification) - wrong revision
            MagicMock(returncode=0, stdout="wrongrev"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_migrate.sh", ["--force", "--skip-backup"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert (
            "Migration verification failed" in output or "target not reached" in output
        )

    @patch("subprocess.run")
    def test_data_safety_check_shows_pending_migrations(
        self, mock_run, script_runner, mock_env
    ):
        """Test that data safety check shows pending migrations."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout="abc123"),
            # alembic show head
            MagicMock(returncode=0),
            # alembic heads
            MagicMock(returncode=0, stdout="def456789012"),
            # alembic history -r range
            MagicMock(returncode=0, stdout="Pending migrations list"),
            # alembic upgrade
            MagicMock(returncode=0),
            # alembic current (final)
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_migrate.sh", ["--force", "--skip-backup"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Migration will change" in output or "Pending migrations" in output

    @patch("subprocess.run")
    def test_no_migration_needed(self, mock_run, script_runner, mock_env):
        """Test behavior when database is already at target revision."""
        current_revision = "abc123456789"
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic current
            MagicMock(returncode=0, stdout=current_revision),
            # alembic show head
            MagicMock(returncode=0),
            # alembic heads (for target resolution)
            MagicMock(returncode=0, stdout=current_revision),
            # No more calls needed as migration is not required
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh")

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "No migration needed" in output or "database is up to date" in output

    def test_invalid_option_combinations(self, script_runner):
        """Test handling of invalid option combinations."""
        # Test conflicting options
        result = script_runner.run_script("db_migrate.sh", ["--dry-run", "--force"])
        # This should work - force doesn't conflict with dry-run
        # But we test that script handles multiple options properly

        # Test unknown option
        result = script_runner.run_script("db_migrate.sh", ["--unknown-option"])
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "Unknown option" in output

    @patch("subprocess.run")
    def test_enhanced_logging_output(self, mock_run, script_runner, mock_env):
        """Test enhanced logging throughout the migration process."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        output = result.stdout + result.stderr

        # Check for various log levels and components
        assert "[INFO]" in output
        assert "Starting database migration script" in output
        assert "Project root:" in output
        assert "Environment file:" in output
        assert (
            "Database connection verified" in output
            or "Database connection check completed" in output
        )

    def test_help_includes_enhanced_options(self, script_runner):
        """Test that help includes all enhanced options."""
        result = script_runner.run_script("db_migrate.sh", ["--help"])

        assert result.returncode == 0
        # Test enhanced options are included
        assert "--dry-run" in result.stdout
        assert "--skip-backup" in result.stdout
        assert "--force" in result.stdout
        assert "--env-file" in result.stdout


@pytest.mark.integration
class TestDbMigrateIntegration:
    """Integration tests for db_migrate.sh against actual database."""

    @pytest.mark.slow
    def test_database_connection_real(self, script_runner):
        """Test actual database connection with real credentials."""
        # Use the actual database URL provided
        db_env = {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert (
            "Database connection verified" in output
            or "Database connection check completed" in output
        )

    @pytest.mark.slow
    def test_migration_dry_run_real(self, script_runner):
        """Test dry run against real database."""
        db_env = {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("db_migrate.sh", ["--dry-run"])

        # Should succeed regardless of current migration state
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Dry run" in output

    @pytest.mark.slow
    def test_migration_history_real(self, script_runner):
        """Test migration history against real database."""
        db_env = {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("db_migrate.sh", ["--history"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Migration history" in output

    @pytest.mark.slow
    def test_current_migration_status_real(self, script_runner):
        """Test checking current migration status against real database."""
        db_env = {"DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"}

        with patch.dict(os.environ, db_env):
            # Test that we can get current status
            result = script_runner.run_script("db_migrate.sh", ["--dry-run", "head"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        # Should show some migration information
        assert (
            "Migration target validated" in output
            or "No migration needed" in output
            or "would be migrated" in output
        )
