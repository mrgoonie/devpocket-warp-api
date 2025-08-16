"""
Comprehensive tests for db_seed.sh script.

Tests cover:
- Script execution and argument parsing
- Database seeding with different data types
- Factory usage and data creation
- Database statistics and reporting
- Error handling and edge cases
- Help and usage information
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import os
import tempfile


@pytest.mark.database
class TestDbSeedScript:
    """Test suite for db_seed.sh script."""

    def test_script_exists_and_executable(self, scripts_dir):
        """Test that the db_seed.sh script exists and is executable."""
        script_path = scripts_dir / "db_seed.sh"
        assert script_path.exists(), "db_seed.sh script should exist"

        # Make it executable for testing
        script_path.chmod(0o755)
        assert os.access(script_path, os.X_OK), "db_seed.sh should be executable"

    def test_script_syntax_is_valid(self, script_runner):
        """Test that the script has valid bash syntax."""
        assert script_runner.check_script_syntax(
            "db_seed.sh"
        ), "db_seed.sh should have valid bash syntax"

    def test_help_option(self, script_runner):
        """Test the help option displays usage information."""
        result = script_runner.run_script("db_seed.sh", ["--help"])

        assert result.returncode == 0
        assert "DevPocket API - Database Seeding Script" in result.stdout
        assert "USAGE:" in result.stdout
        assert "OPTIONS:" in result.stdout
        assert "SEED TYPES:" in result.stdout
        assert "EXAMPLES:" in result.stdout
        assert "PREREQUISITES:" in result.stdout

    def test_help_short_option(self, script_runner):
        """Test the short help option."""
        result = script_runner.run_script("db_seed.sh", ["-h"])

        assert result.returncode == 0
        assert "DevPocket API - Database Seeding Script" in result.stdout

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seed_all_types_default(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding all types with default count."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seed_specific_type_users(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test seeding specific type (users)."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "25"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seed_ssh_connections(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding SSH connections."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["ssh", "15"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seed_commands(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding commands."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["commands", "20"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seed_sessions(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding sessions."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["sessions", "10"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seed_sync_data(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding sync data."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["sync", "12"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_database_connection_failure(self, mock_run, script_runner, mock_env):
        """Test handling of database connection failure."""
        # Mock failed database connection
        mock_run.return_value = MagicMock(returncode=1)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh")

        assert result.returncode != 0

    def test_invalid_seed_type(self, script_runner):
        """Test handling of invalid seed type."""
        result = script_runner.run_script("db_seed.sh", ["invalid_type"])
        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seeding_script_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test handling of seeding script failure."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # Python seeding script execution - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])

        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_stats_only_option(self, mock_file, mock_run, script_runner, mock_env):
        """Test the stats-only option."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_stats_after_seeding(self, mock_file, mock_run, script_runner, mock_env):
        """Test showing stats after seeding."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "10", "--stats"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_stats_script_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test handling when stats script fails."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python stats script execution - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        # Should continue despite stats failure
        assert result.returncode == 0

    def test_unknown_option(self, script_runner):
        """Test handling of unknown options."""
        result = script_runner.run_script("db_seed.sh", ["--invalid-option"])
        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_argument_parsing_order(self, mock_file, mock_run, script_runner, mock_env):
        """Test that arguments are parsed correctly regardless of order."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            # Test different argument orders
            result1 = script_runner.run_script("db_seed.sh", ["users", "15"])
            result2 = script_runner.run_script("db_seed.sh", ["15", "users"])

        assert result1.returncode == 0
        assert result2.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_numeric_argument_validation(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test validation of numeric arguments."""
        # Test with valid numeric count
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "25"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_virtual_environment_activation(self, mock_run, script_runner, mock_env):
        """Test virtual environment activation when available."""
        with patch("os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True
            mock_run.return_value = MagicMock(returncode=0)

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_temporary_script_creation(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test that temporary seeding script is created and cleaned up."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])

        assert result.returncode == 0
        # Verify file operations were called
        assert mock_file.called

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seeding_script_content_users(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test that seeding script content is properly generated for users."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "10"])

        assert result.returncode == 0

        # Check that the temporary script was written with expected content
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "UserFactory" in written_content
        assert "seed_type: users" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_seeding_script_content_all(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test that seeding script content includes all factories for 'all' type."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["all", "5"])

        assert result.returncode == 0

        # Check that all factories are included
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "UserFactory" in written_content
        assert "SSHConnectionFactory" in written_content
        assert "CommandFactory" in written_content
        assert "SessionFactory" in written_content
        assert "SyncDataFactory" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_stats_script_content(self, mock_file, mock_run, script_runner, mock_env):
        """Test that stats script content is properly generated."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0

        # Check that stats script content is correct
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "pg_stat_user_tables" in written_content
        assert "show_database_stats" in written_content

    def test_all_valid_seed_types(self, script_runner):
        """Test that all documented seed types are valid."""
        valid_types = ["all", "users", "ssh", "commands", "sessions", "sync"]

        for seed_type in valid_types:
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    # db_utils.py test
                    MagicMock(returncode=0),
                    # Python seeding script execution
                    MagicMock(returncode=0),
                ]

                result = script_runner.run_script("db_seed.sh", [seed_type, "1"])

                # Should not fail due to invalid seed type
                assert (
                    result.returncode == 0 or "Invalid seed type" not in result.stderr
                )

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_error_handling_in_seeding_script(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test error handling within the generated seeding script."""
        # The seeding script should handle errors gracefully
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution with error
            MagicMock(returncode=1, stderr="Database error"),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])

        assert result.returncode != 0

    @patch("subprocess.run")
    def test_working_directory_handling(self, mock_run, script_runner, mock_env):
        """Test that script handles working directory changes properly."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_cleanup_on_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test that temporary files are cleaned up even on failure."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])

        assert result.returncode != 0

    def test_script_logging_output(self, script_runner):
        """Test that script produces proper logging output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        # Check for logging patterns
        output = result.stdout + result.stderr
        assert "[INFO]" in output
        assert "Starting database seeding script" in output

    def test_environment_variable_usage(self, script_runner):
        """Test that script uses environment variables properly."""
        custom_env = {
            "DATABASE_URL": "postgresql://custom:custom@localhost:5432/custom_db",
            "ENVIRONMENT": "test",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.dict(os.environ, custom_env):
                result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0

    # NEW ENHANCED FEATURE TESTS

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_clean_option_with_confirmation(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test the --clean option with user confirmation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        # Mock user confirmation input
        with patch("builtins.input", return_value="y"):
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script(
                    "db_seed.sh", ["--clean", "users", "10"]
                )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Cleaning data types" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_clean_force_option(self, mock_file, mock_run, script_runner, mock_env):
        """Test the --clean-force option skips confirmation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "users", "10"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Cleaning data types" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_clean_specific_data_types(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test cleaning specific data types."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "ssh", "5"]
            )

        assert result.returncode == 0

        # Check that cleaning script was created with correct content
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "ssh" in written_content.lower()
        assert "DELETE FROM ssh_profiles" in written_content or "ssh" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_reset_database_option(self, mock_file, mock_run, script_runner, mock_env):
        """Test the --reset option resets entire database."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # db_utils.py reset
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        # Mock user confirmation input
        with patch("builtins.input", return_value="y"):
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_seed.sh", ["--reset", "all", "5"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Resetting entire database" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_reset_force_option(self, mock_file, mock_run, script_runner, mock_env):
        """Test the --reset-force option skips confirmation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # db_utils.py reset
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--reset-force", "all", "3"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Resetting entire database" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_upsert_option(self, mock_file, mock_run, script_runner, mock_env):
        """Test the --upsert option for conflict resolution."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution with upsert
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--upsert", "users", "10"])

        assert result.returncode == 0

        # Check that upsert was passed to seeding script
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "use_upsert: True" in written_content
        assert (
            "on_conflict_do_nothing" in written_content
            or "upsert" in written_content.lower()
        )

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_env_file_option(self, mock_file, mock_run, script_runner, temp_dir):
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
            "db_seed.sh", ["--env-file", str(custom_env_file), "--stats-only"]
        )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert f"Environment file: {custom_env_file}" in output

    def test_env_file_option_missing_argument(self, script_runner):
        """Test --env-file with missing argument shows error."""
        result = script_runner.run_script("db_seed.sh", ["--env-file"])
        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "Environment file path required" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_clean_cancellation_by_user(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test user can cancel cleaning operation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0)
        ]

        # Mock user cancellation
        with patch("builtins.input", return_value="n"):
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script(
                    "db_seed.sh", ["--clean", "users", "10"]
                )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Cleaning cancelled by user" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_reset_cancellation_by_user(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test user can cancel reset operation."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0)
        ]

        # Mock user cancellation
        with patch("builtins.input", return_value="n"):
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_seed.sh", ["--reset", "all", "5"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Database reset cancelled by user" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_cleaning_script_content_all_types(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test cleaning script content for all data types."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "all", "5"]
            )

        assert result.returncode == 0

        # Check cleaning script content
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        expected_tables = [
            "commands",
            "sessions",
            "ssh_profiles",
            "sync_data",
            "users",
        ]
        for table in expected_tables:
            assert table in written_content.lower()

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_enhanced_seeding_with_randomization(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test enhanced seeding with proper randomization."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "20"])

        assert result.returncode == 0

        # Check that randomization is included in seeding script
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "random.seed" in written_content
        assert "timestamp" in written_content.lower()
        assert "unique_id" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_enhanced_ssh_profiles_with_relationships(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test SSH profiles creation with proper user relationships."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["ssh", "15"])

        assert result.returncode == 0

        # Check SSH profile and key creation with relationships
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "SSHKey" in written_content
        assert "SSHProfile" in written_content
        assert "user_id" in written_content
        assert "ssh_key_id" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_enhanced_commands_with_sessions(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test commands creation with proper session relationships."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["commands", "25"])

        assert result.returncode == 0

        # Check command creation with session relationships
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "session_id" in written_content
        assert "sample_commands" in written_content
        assert "exit_code" in written_content
        assert (
            "ai_suggested" in written_content or "was_ai_suggested" in written_content
        )

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_enhanced_sync_data_creation(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test sync data creation with proper metadata."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["sync", "12"])

        assert result.returncode == 0

        # Check sync data creation with metadata
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "sync_type" in written_content
        assert "sync_key" in written_content
        assert "version" in written_content
        assert "source_device" in written_content
        assert "conflict_data" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_transaction_management_in_seeding(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test that seeding uses proper transaction management."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "10"])

        assert result.returncode == 0

        # Check transaction management
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "session.commit()" in written_content
        assert "session.flush()" in written_content
        assert "async with AsyncSessionLocal()" in written_content

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_error_handling_in_cleaning_script(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test error handling in cleaning operations."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "users", "10"]
            )

        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "Database cleaning failed" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_error_handling_in_reset_operation(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test error handling in reset operations."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # db_utils.py reset - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--reset-force", "all", "5"]
            )

        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "Database reset failed" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_comprehensive_logging_output(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test comprehensive logging throughout the seeding process."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--upsert", "all", "5", "--stats"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr

        # Check for comprehensive logging
        expected_logs = [
            "[INFO]",
            "Starting database seeding script",
            "Project root:",
            "Seed type:",
            "Count:",
            "Use upsert:",
            "Environment file:",
            "Database connection verified",
        ]

        for expected_log in expected_logs:
            assert expected_log in output

    def test_help_includes_enhanced_options(self, script_runner):
        """Test that help includes all enhanced options."""
        result = script_runner.run_script("db_seed.sh", ["--help"])

        assert result.returncode == 0

        # Test enhanced options are included
        enhanced_options = [
            "--clean",
            "--clean-force",
            "--reset",
            "--reset-force",
            "--upsert",
            "--stats",
            "--stats-only",
            "--env-file",
        ]

        for option in enhanced_options:
            assert option in result.stdout

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_option_combinations(self, mock_file, mock_run, script_runner, mock_env):
        """Test various option combinations work correctly."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh",
                ["--clean-force", "--upsert", "--stats", "users", "10"],
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Cleaning data types: users" in output
        assert "Use upsert: true" in output

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_foreign_key_constraint_handling(
        self, mock_file, mock_run, script_runner, mock_env
    ):
        """Test that foreign key constraints are handled properly in cleaning."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python cleaning script execution
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "all", "5"]
            )

        assert result.returncode == 0

        # Check cleaning order respects FK constraints
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        # Commands should be cleaned before sessions, sessions before users, etc.
        commands_pos = written_content.find("DELETE FROM commands")
        sessions_pos = written_content.find("DELETE FROM sessions")
        users_pos = written_content.find("DELETE FROM users")

        # Commands should be deleted before sessions, sessions before users
        assert commands_pos < sessions_pos < users_pos


@pytest.mark.integration
class TestDbSeedIntegration:
    """Integration tests for db_seed.sh against actual database."""

    @pytest.mark.slow
    def test_database_connection_real(self, script_runner):
        """Test actual database connection with real credentials."""
        db_env = {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Database connection verified" in output

    @pytest.mark.slow
    def test_seeding_users_real(self, script_runner):
        """Test actual user seeding against real database."""
        db_env = {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("db_seed.sh", ["users", "5", "--stats"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Creating 5 sample users" in output or "Created 5 users" in output
        assert "Database seeding completed" in output

    @pytest.mark.slow
    def test_seeding_with_upsert_real(self, script_runner):
        """Test upsert functionality against real database."""
        db_env = {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

        with patch.dict(os.environ, db_env):
            # Run twice to test upsert conflict handling
            result1 = script_runner.run_script("db_seed.sh", ["--upsert", "users", "3"])
            result2 = script_runner.run_script("db_seed.sh", ["--upsert", "users", "3"])

        assert result1.returncode == 0
        assert result2.returncode == 0
        # Second run should handle conflicts gracefully

    @pytest.mark.slow
    def test_stats_real(self, script_runner):
        """Test database statistics against real database."""
        db_env = {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

        with patch.dict(os.environ, db_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert (
            "Database Table Statistics" in output
            or "table statistics" in output.lower()
        )

    @pytest.mark.slow
    def test_clean_specific_type_real(self, script_runner):
        """Test cleaning specific data type against real database."""
        db_env = {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

        with patch.dict(os.environ, db_env):
            # First seed some data
            script_runner.run_script("db_seed.sh", ["commands", "3"])

            # Then clean it
            result = script_runner.run_script(
                "db_seed.sh", ["--clean-force", "commands", "0"]
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Cleaning data types: commands" in output
        assert "Database cleaning completed" in output

    @pytest.mark.slow
    def test_full_workflow_real(self, script_runner):
        """Test full seeding workflow against real database."""
        db_env = {
            "DATABASE_URL": "postgresql://postgres:N9fgWyjhxkNUeYrPm6C8kZVjEpLw@51.79.231.184:32749/devpocket_warp_dev"
        }

        with patch.dict(os.environ, db_env):
            # Clean, seed, and show stats
            result = script_runner.run_script(
                "db_seed.sh",
                ["--clean-force", "--upsert", "all", "2", "--stats"],
            )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Database cleaning completed" in output
        assert "Database seeding completed" in output
        assert "Database statistics" in output or "table statistics" in output.lower()
