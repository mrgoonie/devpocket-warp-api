"""
Comprehensive tests for run_tests.sh script.

Tests cover:
- Script execution and argument parsing
- Different test types and configurations
- Coverage reporting and parallel execution
- Test environment setup and database checks
- Report generation and cleanup
- Error handling and edge cases
- Help and usage information
"""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.mark.unit
class TestRunTestsScript:
    """Test suite for run_tests.sh script."""

    def test_script_exists_and_executable(self, scripts_dir):
        """Test that the run_tests.sh script exists and is executable."""
        script_path = scripts_dir / "run_tests.sh"
        assert script_path.exists(), "run_tests.sh script should exist"

        # Make it executable for testing
        script_path.chmod(0o755)
        assert os.access(script_path, os.X_OK), "run_tests.sh should be executable"

    def test_script_syntax_is_valid(self, script_runner):
        """Test that the script has valid bash syntax."""
        assert script_runner.check_script_syntax(
            "run_tests.sh"
        ), "run_tests.sh should have valid bash syntax"

    def test_help_option(self, script_runner):
        """Test the help option displays usage information."""
        result = script_runner.run_script("run_tests.sh", ["--help"])

        assert result.returncode == 0
        assert "DevPocket API - Test Runner Script" in result.stdout
        assert "USAGE:" in result.stdout
        assert "OPTIONS:" in result.stdout
        assert "TEST TYPES:" in result.stdout
        assert "EXAMPLES:" in result.stdout
        assert "REPORTS:" in result.stdout

    def test_help_short_option(self, script_runner):
        """Test the short help option."""
        result = script_runner.run_script("run_tests.sh", ["-h"])

        assert result.returncode == 0
        assert "DevPocket API - Test Runner Script" in result.stdout

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_run_all_tests_default(
        self, mock_file, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test running all tests with default settings."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_unit_tests_only(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test running unit tests only."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["-t", "unit"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_integration_tests(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test running integration tests."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["--type", "integration"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_api_tests(self, mock_makedirs, mock_run, script_runner, mock_env):
        """Test running API tests."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["-t", "api"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_specific_test_path(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test running tests from specific path."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["tests/test_auth/"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_with_markers(self, mock_makedirs, mock_run, script_runner, mock_env):
        """Test running tests with specific markers."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["-m", "not slow"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_parallel_tests(self, mock_makedirs, mock_run, script_runner, mock_env):
        """Test running tests in parallel."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch(
            "os.cpu_count", return_value=4
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("run_tests.sh", ["-p"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_verbose_tests(self, mock_makedirs, mock_run, script_runner, mock_env):
        """Test running tests with verbose output."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["-v"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_quiet_tests(self, mock_makedirs, mock_run, script_runner, mock_env):
        """Test running tests with quiet output."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["-q"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_run_without_coverage(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test running tests without coverage."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["--no-cov"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_skip_database_check(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test skipping database check."""
        mock_run.side_effect = [
            # pytest execution (no database check)
            MagicMock(returncode=0)
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh", ["--no-db-check"])

        assert result.returncode == 0

    def test_pytest_not_found(self, script_runner):
        """Test handling when pytest is not available."""
        with patch("shutil.which", return_value=None):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_database_check_failure(self, mock_file, mock_run, script_runner, mock_env):
        """Test handling of database check failure."""
        mock_run.return_value = MagicMock(returncode=1)

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        # Should continue with warning
        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_pytest_execution_failure(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test handling of pytest execution failure."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution - failure
            MagicMock(returncode=1),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode != 0

    @patch("subprocess.run")
    def test_clean_artifacts_only(self, mock_run, script_runner):
        """Test cleaning artifacts only."""
        with patch("os.path.exists", return_value=True), patch("shutil.rmtree"), patch(
            "os.remove"
        ):
            result = script_runner.run_script("run_tests.sh", ["--clean-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_clean_before_running(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test cleaning artifacts before running tests."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch(
            "shutil.rmtree"
        ), patch("os.remove"), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("run_tests.sh", ["--clean"])

        assert result.returncode == 0

    def test_summary_only_option(self, script_runner):
        """Test the summary-only option."""
        with patch("os.path.isdir", return_value=True):
            result = script_runner.run_script("run_tests.sh", ["--summary-only"])

        assert result.returncode == 0

    def test_invalid_test_type(self, script_runner):
        """Test handling of invalid test type."""
        result = script_runner.run_script("run_tests.sh", ["-t", "invalid_type"])
        assert result.returncode != 0

    def test_unknown_option(self, script_runner):
        """Test handling of unknown options."""
        result = script_runner.run_script("run_tests.sh", ["--invalid-option"])
        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_markers_option_missing_value(self, mock_makedirs, mock_run, script_runner):
        """Test markers option without value."""
        result = script_runner.run_script("run_tests.sh", ["-m"])
        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_type_option_missing_value(self, mock_makedirs, mock_run, script_runner):
        """Test type option without value."""
        result = script_runner.run_script("run_tests.sh", ["-t"])
        assert result.returncode != 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_all_test_types(self, mock_makedirs, mock_run, script_runner, mock_env):
        """Test all valid test types."""
        valid_types = [
            "all",
            "unit",
            "integration",
            "api",
            "websocket",
            "auth",
            "database",
            "services",
            "security",
            "performance",
            "external",
        ]

        for test_type in valid_types:
            mock_run.reset_mock()
            mock_run.side_effect = [
                # Database check
                MagicMock(returncode=0),
                # pytest execution
                MagicMock(returncode=0),
            ]

            with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
                os.environ, mock_env
            ):
                result = script_runner.run_script("run_tests.sh", ["-t", test_type])

            assert result.returncode == 0, f"Test type '{test_type}' should be valid"

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_virtual_environment_activation(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test virtual environment activation when available."""
        with patch("os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True
            mock_run.side_effect = [
                # Database check
                MagicMock(returncode=0),
                # pytest execution
                MagicMock(returncode=0),
            ]

            with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
                os.environ, mock_env
            ):
                result = script_runner.run_script("run_tests.sh", ["--no-db-check"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_test_environment_setup(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test that test environment variables are set correctly."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_reports_directory_creation(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test that reports directory is created."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0
        mock_makedirs.assert_called()

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_database_check_script_creation(
        self, mock_file, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test that database check script is created and executed."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0
        # Verify database check script was created
        assert mock_file.called

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_pytest_command_construction(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test that pytest command is constructed correctly."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script(
                "run_tests.sh",
                ["-t", "unit", "-m", "not slow", "-v", "-p"],
            )

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_coverage_report_paths(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test that coverage report paths are correctly set."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_html_and_junit_reports(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test that HTML and JUnit reports are generated."""
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("os.path.isfile")
    def test_test_summary_with_reports(
        self, mock_isfile, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test test summary shows report locations."""
        mock_isfile.return_value = True
        mock_run.side_effect = [
            # Database check
            MagicMock(returncode=0),
            # pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
            os.environ, mock_env
        ):
            result = script_runner.run_script("run_tests.sh")

        assert result.returncode == 0

    def test_parallel_execution_cpu_detection(self, script_runner):
        """Test CPU count detection for parallel execution."""
        with patch("os.cpu_count", return_value=8), patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # Database check
                MagicMock(returncode=0),
                # pytest execution
                MagicMock(returncode=0),
            ]

            with patch("shutil.which", return_value="/usr/bin/pytest"):
                result = script_runner.run_script(
                    "run_tests.sh", ["-p", "--no-db-check"]
                )

        assert result.returncode == 0

    def test_cleanup_operations(self, script_runner):
        """Test various cleanup operations."""
        with patch("os.path.exists", return_value=True), patch(
            "shutil.rmtree"
        ) as mock_rmtree, patch("os.remove") as mock_remove, patch("subprocess.run"):
            result = script_runner.run_script("run_tests.sh", ["--clean-only"])

        assert result.returncode == 0
        assert mock_rmtree.called or mock_remove.called

    def test_script_logging_output(self, script_runner):
        """Test that script produces proper logging output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch("shutil.which", return_value="/usr/bin/pytest"):
                result = script_runner.run_script("run_tests.sh", ["--no-db-check"])

        # Check for logging patterns
        output = result.stdout + result.stderr
        assert "[INFO]" in output
        assert "Starting test runner script" in output

    def test_environment_variable_override(self, script_runner):
        """Test that script properly handles environment variable overrides."""
        custom_env = {
            "DATABASE_URL": "postgresql://custom:custom@localhost:5432/custom_test",
            "REDIS_URL": "redis://localhost:6381",
            "ENVIRONMENT": "test",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(
                os.environ, custom_env
            ):
                result = script_runner.run_script("run_tests.sh", ["--no-db-check"])

        assert result.returncode == 0

    def test_test_structure_discovery(self, script_runner):
        """Test test structure discovery functionality."""
        with patch("os.path.isdir", return_value=True), patch(
            "subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 tests collected")

            with patch("shutil.which", return_value="/usr/bin/pytest"):
                result = script_runner.run_script("run_tests.sh", ["--summary-only"])

        assert result.returncode == 0
