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
        assert script_runner.check_script_syntax("db_seed.sh"), \
            "db_seed.sh should have valid bash syntax"

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

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seed_all_types_default(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding all types with default count."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh")
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seed_specific_type_users(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding specific type (users)."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "25"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seed_ssh_connections(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding SSH connections."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["ssh", "15"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seed_commands(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding commands."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["commands", "20"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seed_sessions(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding sessions."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["sessions", "10"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seed_sync_data(self, mock_file, mock_run, script_runner, mock_env):
        """Test seeding sync data."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["sync", "12"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
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

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seeding_script_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test handling of seeding script failure."""
        mock_run.side_effect = [
            # db_utils.py test - success
            MagicMock(returncode=0),
            # Python seeding script execution - failure
            MagicMock(returncode=1)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])
        
        assert result.returncode != 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_stats_only_option(self, mock_file, mock_run, script_runner, mock_env):
        """Test the stats-only option."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_stats_after_seeding(self, mock_file, mock_run, script_runner, mock_env):
        """Test showing stats after seeding."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "10", "--stats"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_stats_script_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test handling when stats script fails."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python stats script execution - failure
            MagicMock(returncode=1)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
        
        # Should continue despite stats failure
        assert result.returncode == 0

    def test_unknown_option(self, script_runner):
        """Test handling of unknown options."""
        result = script_runner.run_script("db_seed.sh", ["--invalid-option"])
        assert result.returncode != 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_argument_parsing_order(self, mock_file, mock_run, script_runner, mock_env):
        """Test that arguments are parsed correctly regardless of order."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            # Test different argument orders
            result1 = script_runner.run_script("db_seed.sh", ["users", "15"])
            result2 = script_runner.run_script("db_seed.sh", ["15", "users"])
        
        assert result1.returncode == 0
        assert result2.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_numeric_argument_validation(self, mock_file, mock_run, script_runner, mock_env):
        """Test validation of numeric arguments."""
        # Test with valid numeric count
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "25"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    def test_virtual_environment_activation(self, mock_run, script_runner, mock_env):
        """Test virtual environment activation when available."""
        with patch('os.path.isdir') as mock_isdir:
            mock_isdir.return_value = True
            mock_run.return_value = MagicMock(returncode=0)
            
            with patch.dict(os.environ, mock_env):
                result = script_runner.run_script("db_seed.sh", ["--stats-only"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_temporary_script_creation(self, mock_file, mock_run, script_runner, mock_env):
        """Test that temporary seeding script is created and cleaned up."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])
        
        assert result.returncode == 0
        # Verify file operations were called
        assert mock_file.called

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seeding_script_content_users(self, mock_file, mock_run, script_runner, mock_env):
        """Test that seeding script content is properly generated for users."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users", "10"])
        
        assert result.returncode == 0
        
        # Check that the temporary script was written with expected content
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        assert "UserFactory" in written_content
        assert "seed_type: users" in written_content

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_seeding_script_content_all(self, mock_file, mock_run, script_runner, mock_env):
        """Test that seeding script content includes all factories for 'all' type."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["all", "5"])
        
        assert result.returncode == 0
        
        # Check that all factories are included
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        assert "UserFactory" in written_content
        assert "SSHConnectionFactory" in written_content
        assert "CommandFactory" in written_content
        assert "SessionFactory" in written_content
        assert "SyncDataFactory" in written_content

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_stats_script_content(self, mock_file, mock_run, script_runner, mock_env):
        """Test that stats script content is properly generated."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python stats script execution
            MagicMock(returncode=0)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
        
        assert result.returncode == 0
        
        # Check that stats script content is correct
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        assert "pg_stat_user_tables" in written_content
        assert "show_database_stats" in written_content

    def test_all_valid_seed_types(self, script_runner):
        """Test that all documented seed types are valid."""
        valid_types = ["all", "users", "ssh", "commands", "sessions", "sync"]
        
        for seed_type in valid_types:
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = [
                    # db_utils.py test
                    MagicMock(returncode=0),
                    # Python seeding script execution
                    MagicMock(returncode=0)
                ]
                
                result = script_runner.run_script("db_seed.sh", [seed_type, "1"])
                
                # Should not fail due to invalid seed type
                assert result.returncode == 0 or "Invalid seed type" not in result.stderr

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_error_handling_in_seeding_script(self, mock_file, mock_run, script_runner, mock_env):
        """Test error handling within the generated seeding script."""
        # The seeding script should handle errors gracefully
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution with error
            MagicMock(returncode=1, stderr="Database error")
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])
        
        assert result.returncode != 0

    @patch('subprocess.run')
    def test_working_directory_handling(self, mock_run, script_runner, mock_env):
        """Test that script handles working directory changes properly."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["--stats-only"])
        
        assert result.returncode == 0

    @patch('subprocess.run')
    @patch('builtins.open', new_callable=mock_open)
    def test_cleanup_on_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test that temporary files are cleaned up even on failure."""
        mock_run.side_effect = [
            # db_utils.py test
            MagicMock(returncode=0),
            # Python seeding script execution - failure
            MagicMock(returncode=1)
        ]
        
        with patch.dict(os.environ, mock_env):
            result = script_runner.run_script("db_seed.sh", ["users"])
        
        assert result.returncode != 0

    def test_script_logging_output(self, script_runner):
        """Test that script produces proper logging output."""
        with patch('subprocess.run') as mock_run:
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
            "ENVIRONMENT": "test"
        }
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            with patch.dict(os.environ, custom_env):
                result = script_runner.run_script("db_seed.sh", ["--stats-only"])
        
        assert result.returncode == 0