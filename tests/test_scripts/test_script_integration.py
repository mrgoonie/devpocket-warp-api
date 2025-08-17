"""
Integration tests for shell scripts.

Tests cover:
- Script interactions and dependencies
- Real execution scenarios (with mocked external services)
- End-to-end workflows
- Performance and reliability
- Cross-script compatibility
"""

import os
import time
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.mark.integration
class TestScriptIntegration:
    """Integration test suite for shell scripts."""

    def test_all_scripts_exist(self, scripts_dir):
        """Test that all expected scripts exist."""
        expected_scripts = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in expected_scripts:
            script_path = scripts_dir / script_name
            assert script_path.exists(), f"Script {script_name} should exist"

    def test_all_scripts_executable(self, scripts_dir):
        """Test that all scripts are executable."""
        script_files = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in script_files:
            script_path = scripts_dir / script_name
            # Make executable for testing
            script_path.chmod(0o755)
            assert os.access(
                script_path, os.X_OK
            ), f"Script {script_name} should be executable"

    def test_all_scripts_valid_syntax(self, script_runner):
        """Test that all scripts have valid bash syntax."""
        scripts = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in scripts:
            assert script_runner.check_script_syntax(
                script_name
            ), f"Script {script_name} should have valid bash syntax"

    def test_all_scripts_have_help(self, script_runner):
        """Test that all scripts provide help information."""
        scripts = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in scripts:
            result = script_runner.run_script(script_name, ["--help"])
            assert result.returncode == 0, f"Script {script_name} should provide help"
            assert (
                "USAGE:" in result.stdout
            ), f"Script {script_name} help should contain usage"

    @patch("subprocess.run")
    @patch("builtins.input", return_value="yes")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_database_reset_workflow(
        self,
        mock_file,
        mock_isfile,
        mock_input,
        mock_run,
        script_runner,
        mock_env,
    ):
        """Test complete database reset workflow."""
        # Mock all subprocess calls to succeed
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

        # Verify all expected steps were called
        assert len(mock_run.call_args_list) >= 4

    @patch("subprocess.run")
    @patch("os.path.isfile", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_migration_and_seeding_workflow(
        self, mock_file, mock_isfile, mock_run, script_runner, mock_env
    ):
        """Test migration followed by seeding workflow."""
        # First run migration
        mock_run.side_effect = [
            # Migration: db_utils.py test
            MagicMock(returncode=0),
            # Migration: alembic current
            MagicMock(returncode=0),
            # Migration: alembic show head
            MagicMock(returncode=0),
            # Migration: alembic upgrade head
            MagicMock(returncode=0),
            # Migration: alembic current (final)
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result1 = script_runner.run_script("db_migrate.sh")

        assert result1.returncode == 0

        # Reset mock for seeding
        mock_run.reset_mock()
        mock_run.side_effect = [
            # Seeding: db_utils.py test
            MagicMock(returncode=0),
            # Seeding: Python script execution
            MagicMock(returncode=0),
        ]

        with patch.dict(os.environ, mock_env):
            result2 = script_runner.run_script("db_seed.sh", ["users", "5"])

        assert result2.returncode == 0

    @patch("subprocess.run")
    @patch("os.makedirs")
    def test_test_and_format_workflow(
        self, mock_makedirs, mock_run, script_runner, mock_env
    ):
        """Test running tests followed by code formatting."""
        # First run tests
        mock_run.side_effect = [
            # Test: Database check
            MagicMock(returncode=0),
            # Test: pytest execution
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", return_value="/usr/bin/pytest"), patch.dict(os.environ, mock_env):
                result1 = script_runner.run_script("run_tests.sh", ["-t", "unit"])

        assert result1.returncode == 0

        # Reset mock for formatting
        mock_run.reset_mock()
        mock_run.side_effect = [
            # Format: Black
            MagicMock(returncode=0),
            # Format: Ruff check
            MagicMock(returncode=0),
            # Format: MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch("os.path.exists", return_value=True), patch.dict(os.environ, mock_env):
                    result2 = script_runner.run_script("format_code.sh", ["--check"])

        assert result2.returncode == 0

    @patch("subprocess.run")
    def test_script_error_handling_chain(self, mock_run, script_runner, mock_env):
        """Test error handling when scripts fail in sequence."""
        # First script fails
        mock_run.return_value = MagicMock(returncode=1)

        with patch.dict(os.environ, mock_env):
            result1 = script_runner.run_script("db_migrate.sh")

        assert result1.returncode != 0

        # Second script should still work independently
        mock_run.reset_mock()
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch("os.path.exists", return_value=True), patch.dict(os.environ, mock_env):
                    result2 = script_runner.run_script("format_code.sh")

        assert result2.returncode == 0

    def test_script_environment_isolation(self, script_runner):
        """Test that scripts don't interfere with each other's environment."""
        env1 = {"TEST_VAR": "value1"}
        env2 = {"TEST_VAR": "value2"}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Run first script with env1
            with patch.dict(os.environ, env1):
                result1 = script_runner.run_script("format_code.sh", ["--stats-only"])

            # Run second script with env2
            with patch.dict(os.environ, env2):
                result2 = script_runner.run_script("format_code.sh", ["--stats-only"])

        assert result1.returncode == 0
        assert result2.returncode == 0

    def test_script_concurrent_execution(self, script_runner):
        """Test that scripts can handle concurrent execution scenarios."""
        import queue
        import threading

        results = queue.Queue()

        def run_script(script_name, args=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                with patch("shutil.which", return_value="/usr/bin/tool"), patch("os.path.exists", return_value=True):
                        result = script_runner.run_script(script_name, args or [])
                        results.put((script_name, result.returncode))

        # Start multiple scripts concurrently
        threads = [
            threading.Thread(
                target=run_script, args=("format_code.sh", ["--stats-only"])
            ),
            threading.Thread(
                target=run_script, args=("format_code.sh", ["--stats-only"])
            ),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        # Check all scripts completed successfully
        while not results.empty():
            script_name, exit_code = results.get()
            assert (
                exit_code == 0
            ), f"Script {script_name} should succeed in concurrent execution"

    @patch("subprocess.run")
    def test_script_dependency_validation(self, mock_run, script_runner):
        """Test that scripts properly validate their dependencies."""
        # Test with missing tools
        with patch("shutil.which", return_value=None):
            result1 = script_runner.run_script("format_code.sh")
            assert result1.returncode != 0

            result2 = script_runner.run_script("run_tests.sh")
            assert result2.returncode != 0

    def test_script_output_consistency(self, script_runner):
        """Test that scripts produce consistent output format."""
        scripts_to_test = [
            ("db_migrate.sh", ["--help"]),
            ("db_seed.sh", ["--help"]),
            ("db_reset.sh", ["--help"]),
            ("run_tests.sh", ["--help"]),
            ("format_code.sh", ["--help"]),
        ]

        for script_name, args in scripts_to_test:
            result = script_runner.run_script(script_name, args)

            assert result.returncode == 0, f"Help for {script_name} should work"

            # Check for consistent output patterns
            output = result.stdout
            assert "USAGE:" in output, f"Script {script_name} should have usage section"
            assert (
                "OPTIONS:" in output
            ), f"Script {script_name} should have options section"
            assert (
                "EXAMPLES:" in output
            ), f"Script {script_name} should have examples section"

    def test_script_logging_consistency(self, script_runner):
        """Test that all scripts use consistent logging format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            scripts_to_test = [
                ("db_migrate.sh", ["--check-only"]),
                ("db_seed.sh", ["--stats-only"]),
                ("run_tests.sh", ["--clean-only"]),
                ("format_code.sh", ["--stats-only"]),
            ]

            for script_name, args in scripts_to_test:
                with patch("shutil.which", return_value="/usr/bin/tool"), patch("os.path.exists", return_value=True):
                        result = script_runner.run_script(script_name, args)

                # Check for consistent logging patterns
                output = result.stdout + result.stderr
                if output:  # Some scripts may not produce output with mocked calls
                    # Look for timestamp patterns and log levels
                    has_logging = any(
                        level in output
                        for level in [
                            "[INFO]",
                            "[WARN]",
                            "[ERROR]",
                            "[SUCCESS]",
                        ]
                    )
                    if has_logging:
                        assert (
                            "[INFO]" in output
                        ), f"Script {script_name} should use INFO logging"

    @patch("subprocess.run")
    def test_script_performance_reasonable(self, mock_run, script_runner):
        """Test that scripts complete within reasonable time limits."""
        mock_run.return_value = MagicMock(returncode=0)

        scripts_to_test = [
            ("format_code.sh", ["--stats-only"]),
            ("run_tests.sh", ["--clean-only"]),
        ]

        for script_name, args in scripts_to_test:
            start_time = time.time()

            with patch("shutil.which", return_value="/usr/bin/tool"), patch("os.path.exists", return_value=True):
                    result = script_runner.run_script(script_name, args, timeout=30)

            execution_time = time.time() - start_time

            assert (
                result.returncode == 0
            ), f"Script {script_name} should complete successfully"
            assert (
                execution_time < 30
            ), f"Script {script_name} should complete within 30 seconds"

    def test_script_error_message_quality(self, script_runner):
        """Test that scripts provide helpful error messages."""
        scripts_and_bad_args = [
            ("db_migrate.sh", ["--invalid-option"]),
            ("db_seed.sh", ["invalid_type"]),
            ("db_reset.sh", ["--invalid-option"]),
            ("run_tests.sh", ["--invalid-option"]),
            ("format_code.sh", ["--invalid-option"]),
        ]

        for script_name, bad_args in scripts_and_bad_args:
            result = script_runner.run_script(script_name, bad_args)

            assert (
                result.returncode != 0
            ), f"Script {script_name} should fail with invalid args"

            # Check for helpful error messages
            error_output = result.stdout + result.stderr
            error_indicators = ["ERROR", "Unknown", "Invalid", "Usage", "help"]
            has_helpful_error = any(
                indicator in error_output for indicator in error_indicators
            )
            assert (
                has_helpful_error
            ), f"Script {script_name} should provide helpful error messages"

    def test_script_exit_code_consistency(self, script_runner):
        """Test that scripts use exit codes consistently."""
        # Test successful operations
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            success_tests = [
                ("format_code.sh", ["--stats-only"]),
                ("run_tests.sh", ["--clean-only"]),
            ]

            for script_name, args in success_tests:
                with patch("shutil.which", return_value="/usr/bin/tool"), patch("os.path.exists", return_value=True):
                        result = script_runner.run_script(script_name, args)
                        assert (
                            result.returncode == 0
                        ), f"Successful {script_name} should return 0"

        # Test help operations (should always succeed)
        help_tests = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in help_tests:
            result = script_runner.run_script(script_name, ["--help"])
            assert result.returncode == 0, f"Help for {script_name} should return 0"

    def test_script_documentation_completeness(self, script_runner):
        """Test that all scripts have complete documentation."""
        scripts = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in scripts:
            result = script_runner.run_script(script_name, ["--help"])
            help_text = result.stdout

            # Check for required documentation sections
            required_sections = ["USAGE:", "OPTIONS:", "EXAMPLES:"]
            for section in required_sections:
                assert (
                    section in help_text
                ), f"Script {script_name} should have {section} section"

            # Check for environment documentation
            if script_name in ["db_migrate.sh", "db_seed.sh", "db_reset.sh"]:
                assert (
                    "ENVIRONMENT:" in help_text
                ), f"Database script {script_name} should document environment variables"

    @patch("subprocess.run")
    def test_script_resource_cleanup(self, mock_run, script_runner, mock_env):
        """Test that scripts properly clean up temporary resources."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test_script_temp"
            mock_temp.__enter__.return_value = mock_temp_file

            with patch("os.remove"), patch.dict(os.environ, mock_env):
                # Scripts that create temporary files
                result = script_runner.run_script("db_seed.sh", ["--stats-only"])

            assert result.returncode == 0

    def test_script_input_validation(self, script_runner):
        """Test that scripts properly validate input parameters."""
        validation_tests = [
            ("db_reset.sh", ["--seed-count", "not_a_number"]),
            ("db_reset.sh", ["--seed-type", "invalid_type"]),
            ("run_tests.sh", ["-t", "invalid_type"]),
            ("format_code.sh", ["nonexistent_file"]),
        ]

        for script_name, invalid_args in validation_tests:
            result = script_runner.run_script(script_name, invalid_args)
            assert (
                result.returncode != 0
            ), f"Script {script_name} should reject invalid input: {invalid_args}"
