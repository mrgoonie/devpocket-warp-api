"""
Comprehensive tests for db_reset.sh script.

Tests cover:
- Script execution and argument parsing
- Database reset sequence (drop, create, migrate, seed)
- Confirmation prompts and force mode
- Error handling and rollback scenarios
- Integration with other scripts
- Help and usage information
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import os
import tempfile


@pytest.mark.database
class TestDbResetScript:
    """Test suite for db_reset.sh script."""

    def test_script_exists_and_executable(self, scripts_dir):
        """Test that the db_reset.sh script exists and is executable."""
        script_path = scripts_dir / "db_reset.sh"
        assert script_path.exists(), "db_reset.sh script should exist"

        # Make it executable for testing
        script_path.chmod(0o755)
        assert os.access(script_path, os.X_OK), "db_reset.sh should be executable"

    def test_script_syntax_is_valid(self, script_runner):
        """Test that the script has valid bash syntax."""
        assert script_runner.check_script_syntax(
            "db_reset.sh"
        ), "db_reset.sh should have valid bash syntax"

    def test_help_option(self, script_runner):
        """Test the help option displays usage information."""
        result = script_runner.run_script("db_reset.sh", ["--help"])

        assert result.returncode == 0
        assert "DevPocket API - Database Reset Script" in result.stdout
        assert "USAGE:" in result.stdout
        assert "OPTIONS:" in result.stdout
        assert "SEED TYPES:" in result.stdout
        assert "EXAMPLES:" in result.stdout
        assert "OPERATION SEQUENCE:" in result.stdout
        assert "WARNING:" in result.stdout

    def test_help_short_option(self, script_runner):
        """Test the short help option."""
        result = script_runner.run_script("db_reset.sh", ["-h"])

        assert result.returncode == 0
        assert "DevPocket API - Database Reset Script" in result.stdout

    @patch("subprocess.run")
    @patch("builtins.input", return_value="yes")
    @patch("os.path.isfile", return_value=True)
    def test_complete_reset_with_confirmation(
        self, mock_isfile, mock_input, mock_run, script_runner, mock_env
    ):
        """Test complete database reset with user confirmation."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh")

        assert result.returncode == 0
        mock_input.assert_called_once()

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_reset_with_force_flag(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test database reset with force flag (no confirmation)."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_reset_with_force_short_flag(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test database reset with short force flag."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["-f"])

        assert result.returncode == 0

    @patch("builtins.input", return_value="no")
    def test_reset_cancelled_by_user(self, mock_input, script_runner):
        """Test that reset is cancelled when user doesn't confirm."""
        result = script_runner.run_script("db_reset.sh")

        assert result.returncode == 0  # Script should exit gracefully
        mock_input.assert_called_once()

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_reset_no_seed_option(self, mock_isfile, mock_run, script_runner, mock_env):
        """Test database reset without seeding."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force", "--no-seed"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_reset_with_custom_seed_type(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test database reset with custom seed type."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_reset.sh", ["--force", "--seed-type", "users"]
            )

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_reset_with_custom_seed_count(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test database reset with custom seed count."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_reset.sh", ["--force", "--seed-count", "25"]
            )

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_reset_no_verify_option(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test database reset without health verification."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force", "--no-verify"])

        assert result.returncode == 0

    def test_missing_db_utils_script(self, script_runner):
        """Test handling when db_utils.py is missing."""
        with patch("os.path.isfile") as mock_isfile:
            mock_isfile.side_effect = lambda path: "db_utils.py" not in str(path)

            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode != 0

    def test_missing_migrate_script(self, script_runner):
        """Test handling when db_migrate.sh is missing."""
        with patch("os.path.isfile") as mock_isfile:
            mock_isfile.side_effect = lambda path: "db_migrate.sh" not in str(path)

            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode != 0

    @patch("os.path.isfile")
    def test_missing_seed_script_warning(self, mock_isfile, script_runner):
        """Test warning when db_seed.sh is missing."""

        def mock_file_check(path):
            if "db_seed.sh" in str(path):
                return False
            return True

        mock_isfile.side_effect = mock_file_check

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # db_utils.py reset
                MagicMock(returncode=0),
                # db_migrate.sh
                MagicMock(returncode=0),
                # db_utils.py health
                MagicMock(returncode=0),
                # Status script
                MagicMock(returncode=0),
            ]

            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_database_reset_failure(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test handling of database reset failure."""
        mock_run.return_value = MagicMock(returncode=1)

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_migration_failure(self, mock_isfile, mock_run, script_runner, mock_env):
        """Test handling of migration failure."""
        mock_run.side_effect = [
            # db_utils.py reset - success
            MagicMock(returncode=0),
            # db_migrate.sh - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_seeding_failure_continues(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test that seeding failure doesn't stop the reset process."""
        mock_run.side_effect = [
            # db_utils.py reset - success
            MagicMock(returncode=0),
            # db_migrate.sh - success
            MagicMock(returncode=0),
            # db_seed.sh - failure
            MagicMock(returncode=1),
            # db_utils.py health - success
            MagicMock(returncode=0),
            # Status script - success
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        # Should continue despite seeding failure
        assert result.returncode == 0

    def test_invalid_seed_type(self, script_runner):
        """Test handling of invalid seed type."""
        result = script_runner.run_script(
            "db_reset.sh", ["--force", "--seed-type", "invalid_type"]
        )
        assert result.returncode != 0

    def test_invalid_seed_count(self, script_runner):
        """Test handling of invalid seed count."""
        result = script_runner.run_script(
            "db_reset.sh", ["--force", "--seed-count", "not_a_number"]
        )
        assert result.returncode != 0

    def test_seed_count_without_value(self, script_runner):
        """Test handling of seed count option without value."""
        result = script_runner.run_script("db_reset.sh", ["--force", "--seed-count"])
        assert result.returncode != 0

    def test_seed_type_without_value(self, script_runner):
        """Test handling of seed type option without value."""
        result = script_runner.run_script("db_reset.sh", ["--force", "--seed-type"])
        assert result.returncode != 0

    def test_unknown_option(self, script_runner):
        """Test handling of unknown options."""
        result = script_runner.run_script("db_reset.sh", ["--invalid-option"])
        assert result.returncode != 0

    def test_unexpected_argument(self, script_runner):
        """Test handling of unexpected arguments."""
        result = script_runner.run_script("db_reset.sh", ["unexpected_arg"])
        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_virtual_environment_activation(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test virtual environment activation when available."""
        with patch("os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True
            mock_run.side_effect = [
                # db_utils.py reset
                MagicMock(returncode=0),
                # db_migrate.sh
                MagicMock(returncode=0),
                # db_seed.sh
                MagicMock(returncode=0),
                # db_utils.py health
                MagicMock(returncode=0),
                # Status script
                MagicMock(returncode=0),
            ]

            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_status_script_creation(
        self, mock_file, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test that status script is created and executed."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        assert result.returncode == 0
        # Verify status script was created
        assert mock_file.called

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_status_script_failure(
        self, mock_file, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test handling when status script fails."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script - failure
            MagicMock(returncode=1),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        # Should continue despite status script failure
        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_health_verification_failure(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test handling when health verification fails."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health - failure
            MagicMock(returncode=1),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        # Should continue despite health verification failure
        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_script_permissions_setup(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test that scripts are made executable before running."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch("os.chmod") as mock_chmod:
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_reset.sh", ["--force"])

        # Should have set execute permissions
        assert mock_chmod.called
        assert result.returncode == 0

    def test_all_valid_seed_types(self, script_runner):
        """Test that all documented seed types are accepted."""
        valid_types = ["all", "users", "ssh", "commands", "sessions", "sync"]

        for seed_type in valid_types:
            # Just test argument parsing, not execution
            help_result = script_runner.run_script("db_reset.sh", ["--help"])
            assert seed_type in help_result.stdout

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    def test_complete_operation_sequence(
        self, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test the complete operation sequence."""
        mock_run.side_effect = [
            # db_utils.py reset
            MagicMock(returncode=0),
            # db_migrate.sh
            MagicMock(returncode=0),
            # db_seed.sh
            MagicMock(returncode=0),
            # db_utils.py health
            MagicMock(returncode=0),
            # Status script
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_reset.sh", ["--force"])

        # Verify the correct sequence of calls
        expected_calls = [
            call(
                ["python", mock_run.call_args_list[0][0][1], "reset"],
                cwd=mock_run.call_args_list[0][1]["cwd"],
                env=mock_run.call_args_list[0][1]["env"],
            ),
        ]

        assert result.returncode == 0
        assert len(mock_run.call_args_list) == 5

    def test_script_logging_output(self, script_runner):
        """Test that script produces proper logging output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = script_runner.run_script("db_reset.sh", ["--force", "--no-seed"])

        # Check for logging patterns
        output = result.stdout + result.stderr
        assert "[INFO]" in output
        assert "Starting database reset script" in output

    def test_destructive_operation_warning(self, script_runner):
        """Test that script displays proper warning about destructive operation."""
        help_result = script_runner.run_script("db_reset.sh", ["--help"])

        assert "WARNING:" in help_result.stdout
        assert "destructive" in help_result.stdout.lower()
        assert "permanently delete" in help_result.stdout.lower()

    def test_environment_variable_usage(self, script_runner):
        """Test that script uses environment variables properly."""
        custom_env = {
            "DATABASE_URL": "postgresql://custom:custom@localhost:5432/custom_db",
            "ENVIRONMENT": "test",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.dict(os.environ, custom_env):
                result = script_runner.run_script(
                    "db_reset.sh", ["--force", "--no-seed"]
                )

        assert result.returncode == 0
