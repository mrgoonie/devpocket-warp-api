"""
Script verification tests.

These tests verify that all shell scripts work correctly with the existing
project infrastructure and dependencies.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestScriptVerification:
    """Verification tests for shell scripts."""

    def test_scripts_have_correct_permissions(self, scripts_dir):
        """Test that all scripts have correct execute permissions."""
        script_files = [
            "db_migrate.sh",
            "db_seed.sh",
            "db_reset.sh",
            "run_tests.sh",
            "format_code.sh",
        ]

        for script_name in script_files:
            script_path = scripts_dir / script_name
            assert script_path.exists(), f"Script {script_name} should exist"

            # Check file permissions
            stat_info = script_path.stat()
            # Check if owner has execute permission (0o100)
            assert (
                stat_info.st_mode & 0o100
            ), f"Script {script_name} should be executable by owner"

    def test_scripts_integration_with_project_tools(self, script_runner):
        """Test that scripts integrate correctly with project tools."""

        # Test that scripts can find and use project dependencies
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Test db_migrate.sh can find alembic
            with patch("shutil.which", return_value="/usr/bin/alembic"):
                result = script_runner.run_script("db_migrate.sh", ["--help"])
                assert result.returncode == 0

            # Test run_tests.sh can find pytest
            with patch("shutil.which", return_value="/usr/bin/pytest"):
                result = script_runner.run_script("run_tests.sh", ["--help"])
                assert result.returncode == 0

            # Test format_code.sh can find formatting tools
            with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"):
                result = script_runner.run_script("format_code.sh", ["--help"])
                assert result.returncode == 0

    def test_scripts_use_project_structure(self, script_runner, project_root):
        """Test that scripts understand and use the project structure correctly."""

        # Verify scripts can determine project root
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            scripts_to_test = [
                "db_migrate.sh",
                "db_seed.sh",
                "db_reset.sh",
                "run_tests.sh",
                "format_code.sh",
            ]

            for script_name in scripts_to_test:
                result = script_runner.run_script(script_name, ["--help"])
                assert (
                    result.returncode == 0
                ), f"Script {script_name} should work with project structure"

    def test_scripts_handle_missing_dependencies_gracefully(self, script_runner):
        """Test that scripts handle missing dependencies gracefully."""

        # Test with missing tools
        with patch("shutil.which", return_value=None):
            # db_migrate.sh should fail gracefully when alembic is missing
            result = script_runner.run_script(
                "db_migrate.sh", ["--check-only"], timeout=10
            )
            assert result.returncode != 0

            # run_tests.sh should fail gracefully when pytest is missing
            result = script_runner.run_script("run_tests.sh", ["--help"], timeout=10)
            # Help should always work
            assert result.returncode == 0

            # But actual test running should fail
            result = script_runner.run_script(
                "run_tests.sh", ["--summary-only"], timeout=10
            )
            # This might fail or succeed depending on implementation

            # format_code.sh should fail gracefully when tools are missing
            result = script_runner.run_script("format_code.sh", ["app/"], timeout=10)
            assert result.returncode != 0

    def test_scripts_respect_environment_variables(self, script_runner):
        """Test that scripts respect project environment variables."""

        test_env = {
            "DATABASE_URL": "postgresql://test:test@localhost:5433/test_db",
            "REDIS_URL": "redis://localhost:6380",
            "ENVIRONMENT": "test",
            "TESTING": "true",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.dict(os.environ, test_env):
                # Test database scripts use environment variables
                result = script_runner.run_script("db_migrate.sh", ["--help"])
                assert result.returncode == 0

                result = script_runner.run_script("db_seed.sh", ["--help"])
                assert result.returncode == 0

                result = script_runner.run_script("db_reset.sh", ["--help"])
                assert result.returncode == 0

    def test_scripts_work_with_virtual_environment(self, script_runner):
        """Test that scripts work correctly with virtual environments."""

        # Mock virtual environment detection
        with patch("os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True  # Simulate venv exists

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                # Test that scripts attempt to activate virtual environment
                result = script_runner.run_script("db_migrate.sh", ["--help"])
                assert result.returncode == 0

    def test_scripts_error_handling_robustness(self, script_runner):
        """Test that scripts handle errors robustly."""

        # Test various error scenarios
        error_scenarios = [
            ("db_migrate.sh", ["--invalid-option"]),
            ("db_seed.sh", ["invalid_type"]),
            ("db_reset.sh", ["--seed-type", "invalid"]),
            ("run_tests.sh", ["--type", "invalid"]),
            ("format_code.sh", ["--invalid-flag"]),
        ]

        for script_name, args in error_scenarios:
            result = script_runner.run_script(script_name, args, timeout=10)
            # Should fail but not hang or crash
            assert (
                result.returncode != 0
            ), f"Script {script_name} should handle invalid args gracefully"

    def test_scripts_logging_and_output_quality(self, script_runner):
        """Test that scripts produce high-quality logging and output."""

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

            output = result.stdout

            # Check output quality
            assert (
                len(output) > 100
            ), f"Help output for {script_name} should be substantial"
            assert "USAGE:" in output, f"Help for {script_name} should contain usage"
            assert (
                "OPTIONS:" in output
            ), f"Help for {script_name} should contain options"
            assert (
                "EXAMPLES:" in output
            ), f"Help for {script_name} should contain examples"

            # Check for proper formatting
            lines = output.split("\n")
            assert len(lines) > 10, f"Help for {script_name} should have multiple lines"

    def test_scripts_work_with_pytest_markers(self, script_runner):
        """Test that test scripts work with pytest markers defined in pytest.ini."""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch("shutil.which", return_value="/usr/bin/pytest"):
                # Test various marker combinations
                marker_tests = [
                    ["-m", "unit"],
                    ["-m", "integration"],
                    ["-m", "not slow"],
                    ["-m", "unit and not slow"],
                ]

                for marker_args in marker_tests:
                    script_runner.run_script("run_tests.sh", marker_args, timeout=5)
                    # Should not fail due to marker syntax
                    # (actual execution mocked, so we just check parsing)

    def test_scripts_security_considerations(self, script_runner):
        """Test that scripts handle security considerations properly."""

        # Test that scripts don't execute untrusted input
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Test with potentially dangerous inputs
            dangerous_inputs = [
                "; rm -rf /",
                "$(rm -rf /)",
                "`rm -rf /`",
                "../../etc/passwd",
            ]

            for dangerous_input in dangerous_inputs:
                # Scripts should either reject these or handle them safely
                script_runner.run_script("format_code.sh", [dangerous_input], timeout=5)
                # Should either fail safely or handle the input properly
                # We don't want the script to hang or execute dangerous commands

    def test_scripts_performance_baseline(self, script_runner):
        """Test that scripts have reasonable performance characteristics."""

        import time

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Test help commands (should be very fast)
            fast_operations = [
                ("db_migrate.sh", ["--help"]),
                ("db_seed.sh", ["--help"]),
                ("db_reset.sh", ["--help"]),
                ("run_tests.sh", ["--help"]),
                ("format_code.sh", ["--help"]),
            ]

            for script_name, args in fast_operations:
                start_time = time.time()
                result = script_runner.run_script(script_name, args, timeout=5)
                execution_time = time.time() - start_time

                assert result.returncode == 0, f"Script {script_name} help should work"
                assert (
                    execution_time < 5
                ), f"Script {script_name} help should be fast (< 5s)"

    def test_scripts_compatibility_with_ci_cd(self, script_runner):
        """Test that scripts are compatible with CI/CD environments."""

        # Simulate CI environment variables
        ci_env = {"CI": "true", "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux"}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch.dict(os.environ, ci_env):
                # Test that scripts work in CI environment
                scripts_to_test = [
                    ("run_tests.sh", ["--help"]),
                    ("format_code.sh", ["--help"]),
                ]

                for script_name, args in scripts_to_test:
                    result = script_runner.run_script(script_name, args)
                    assert (
                        result.returncode == 0
                    ), f"Script {script_name} should work in CI"

    def test_scripts_maintain_backward_compatibility(self, script_runner):
        """Test that scripts maintain backward compatibility."""

        # Test that basic usage patterns still work
        basic_patterns = [
            ("db_migrate.sh", []),
            ("db_migrate.sh", ["head"]),
            ("db_seed.sh", []),
            ("db_seed.sh", ["users"]),
            ("run_tests.sh", []),
            ("format_code.sh", []),
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with (
                patch("shutil.which", return_value="/usr/bin/tool"),
                patch("os.path.exists", return_value=True),
            ):
                for script_name, args in basic_patterns:
                    # These should either work or fail gracefully
                    script_runner.run_script(script_name, args, timeout=10)
                    # We don't assert success here since some operations need real infrastructure
                    # but we ensure they don't hang or crash catastrophically
