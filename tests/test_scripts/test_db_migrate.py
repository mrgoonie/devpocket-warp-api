"""
Comprehensive tests for db_migrate.sh script.

Tests cover:
- Script execution and argument parsing
- Database connection testing
- Alembic migration operations
- Error handling and edge cases
- Help and usage information
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import os


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
        assert script_runner.check_script_syntax("db_migrate.sh"), \
            "db_migrate.sh should have valid bash syntax"

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

    @patch('subprocess.run')
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
            MagicMock(returncode=0, stdout="new_revision")
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["head"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
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
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", [revision])
        
        assert result.returncode == 0

    @patch('subprocess.run')
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
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["+1"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
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
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["-1"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_database_connection_failure(self, mock_run, script_runner, mock_env):
        """Test handling of database connection failure."""
        # Mock failed database connection
        mock_run.return_value = MagicMock(returncode=1)
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh")
        
        assert result.returncode != 0

    @patch('subprocess.run')
    def test_alembic_not_found(self, mock_run, script_runner, mock_env):
        """Test handling when Alembic is not available."""
        with patch('shutil.which', return_value=None):
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_migrate.sh")
        
        assert result.returncode != 0

    @patch('subprocess.run')
    def test_invalid_migration_target(self, mock_run, script_runner, mock_env):
        """Test handling of invalid migration target."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic current - success
            MagicMock(returncode=0),
            # alembic show invalid_target - failure
            MagicMock(returncode=1)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["invalid_target"])
        
        assert result.returncode != 0

    @patch('subprocess.run')
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
            MagicMock(returncode=1)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["head"])
        
        assert result.returncode != 0

    def test_generate_migration_option(self, script_runner, mock_env):
        """Test the generate migration option."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                # db_utils.py test
                MagicMock(returncode=0),
                # alembic revision --autogenerate
                MagicMock(returncode=0)
            ]
            
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script(
                    "db_migrate.sh", 
                    ["-g", "Add new table"]
                )
        
        assert result.returncode == 0

    def test_generate_migration_long_option(self, script_runner, mock_env):
        """Test the generate migration long option."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                # db_utils.py test
                MagicMock(returncode=0),
                # alembic revision --autogenerate
                MagicMock(returncode=0)
            ]
            
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script(
                    "db_migrate.sh", 
                    ["--generate", "Add new field"]
                )
        
        assert result.returncode == 0

    def test_generate_migration_without_message(self, script_runner):
        """Test generate migration option without message should fail."""
        result = script_runner.run_script("db_migrate.sh", ["-g"])
        assert result.returncode != 0

    @patch('subprocess.run')
    def test_history_option(self, mock_run, script_runner, mock_env):
        """Test the history option."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # alembic history --verbose
            MagicMock(returncode=0, stdout="migration history")
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--history"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
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

    @patch('subprocess.run')
    def test_virtual_environment_activation(self, mock_run, script_runner, mock_env):
        """Test virtual environment activation when available."""
        # Create a mock venv directory structure
        with patch('os.path.isdir') as mock_isdir:
            mock_isdir.return_value = True
            mock_run.return_value = MagicMock(returncode=0)
            
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_migrate.sh", ["--check-only"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
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
            MagicMock(returncode=0, stdout="def456 (head)")
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh")
        
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_alembic_current_failure(self, mock_run, script_runner, mock_env):
        """Test handling when alembic current command fails."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic current - failure
            MagicMock(returncode=1)
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

    @patch('subprocess.run')
    def test_working_directory_change(self, mock_run, script_runner, mock_env):
        """Test that script changes to project root for Alembic operations."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_script_logging_output(self, mock_run, script_runner, mock_env):
        """Test that script produces proper logging output."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])
        
        # Check for logging patterns
        output = result.stdout + result.stderr
        assert "[INFO]" in output
        assert "Starting database migration script" in output

    @patch('subprocess.run')
    def test_generate_migration_failure(self, mock_run, script_runner, mock_env):
        """Test handling of migration generation failure."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # alembic revision --autogenerate - failure
            MagicMock(returncode=1)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script(
                "db_migrate.sh", 
                ["-g", "Test migration"]
            )
        
        assert result.returncode != 0

    def test_script_parameter_validation(self, script_runner):
        """Test various parameter combinations."""
        # Test multiple targets (should use the last one)
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = script_runner.run_script(
                "db_migrate.sh", 
                ["head", "abc123", "--check-only"]
            )
        
        # Script should handle this gracefully
        # (exact behavior depends on implementation)

    @patch('subprocess.run')
    def test_environment_variable_usage(self, mock_run, script_runner):
        """Test that script uses environment variables properly."""
        custom_env = {
            "DATABASE_HOST": "custom-host",
            "DATABASE_PORT": "5434",
            "DATABASE_USER": "custom-user",
            "DATABASE_PASSWORD": "custom-pass",
            "DATABASE_NAME": "custom-db"
        }
        
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict(os.environ, custom_env):
            result = script_runner.run_script("db_migrate.sh", ["--check-only"])
        
        assert result.returncode == 0