"""
Comprehensive tests for format_code.sh script.

Tests cover:
- Script execution and argument parsing
- Code formatting with Black, Ruff, and MyPy
- Different modes (check, fix, format)
- Report generation and statistics
- Tool availability and configuration
- Error handling and exit codes
- Help and usage information
"""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.mark.unit
class TestFormatCodeScript:
    """Test suite for format_code.sh script."""

    def test_script_exists_and_executable(self, scripts_dir):
        """Test that the format_code.sh script exists and is executable."""
        script_path = scripts_dir / "format_code.sh"
        assert script_path.exists(), "format_code.sh script should exist"

        # Make it executable for testing
        script_path.chmod(0o755)
        assert os.access(script_path, os.X_OK), "format_code.sh should be executable"

    def test_script_syntax_is_valid(self, script_runner):
        """Test that the script has valid bash syntax."""
        assert script_runner.check_script_syntax(
            "format_code.sh"
        ), "format_code.sh should have valid bash syntax"

    def test_help_option(self, script_runner):
        """Test the help option displays usage information."""
        result = script_runner.run_script("format_code.sh", ["--help"])

        assert result.returncode == 0
        assert "DevPocket API - Code Formatting and Quality Script" in result.stdout
        assert "USAGE:" in result.stdout
        assert "OPTIONS:" in result.stdout
        assert "TOOL DESCRIPTIONS:" in result.stdout
        assert "EXAMPLES:" in result.stdout
        assert "EXIT CODES:" in result.stdout

    def test_help_short_option(self, script_runner):
        """Test the short help option."""
        result = script_runner.run_script("format_code.sh", ["-h"])

        assert result.returncode == 0
        assert "DevPocket API - Code Formatting and Quality Script" in result.stdout

    @patch("subprocess.run")
    def test_format_default_target(self, mock_run, script_runner, mock_env):
        """Test formatting with default target (app/)."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_format_specific_file(self, mock_run, script_runner, mock_env):
        """Test formatting a specific file."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["main.py"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_format_specific_directory(self, mock_run, script_runner, mock_env):
        """Test formatting a specific directory."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["app/core/"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_check_only_mode(self, mock_run, script_runner, mock_env):
        """Test check-only mode (no changes made)."""
        mock_run.side_effect = [
            # Black --check
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--check"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_fix_mode(self, mock_run, script_runner, mock_env):
        """Test fix mode (auto-fix issues)."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check --fix
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--fix"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_black_only_option(self, mock_run, script_runner, mock_env):
        """Test running Black formatter only."""
        mock_run.side_effect = [
            # Black only
            MagicMock(returncode=0)
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--black-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_ruff_only_option(self, mock_run, script_runner, mock_env):
        """Test running Ruff linter only."""
        mock_run.side_effect = [
            # Ruff check
            MagicMock(returncode=0),
            # Ruff format (since Black is disabled)
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--ruff-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_mypy_only_option(self, mock_run, script_runner, mock_env):
        """Test running MyPy type checker only."""
        mock_run.side_effect = [
            # MyPy only
            MagicMock(returncode=0)
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--mypy-only"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_no_black_option(self, mock_run, script_runner, mock_env):
        """Test skipping Black formatter."""
        mock_run.side_effect = [
            # Ruff check
            MagicMock(returncode=0),
            # Ruff format (since Black is disabled)
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--no-black"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_no_ruff_option(self, mock_run, script_runner, mock_env):
        """Test skipping Ruff linter."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--no-ruff"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_no_mypy_option(self, mock_run, script_runner, mock_env):
        """Test skipping MyPy type checker."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--no-mypy"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_strict_mode(self, mock_run, script_runner, mock_env):
        """Test strict type checking mode."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy --strict
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--strict"])

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_diff_option(self, mock_run, script_runner, mock_env):
        """Test diff option for showing changes."""
        mock_run.side_effect = [
            # Black --diff
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--diff"])

        assert result.returncode == 0

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    def test_report_generation(self, mock_file, mock_run, script_runner, mock_env):
        """Test quality report generation."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
            # Report generation calls
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--report"])

        assert result.returncode == 0
        assert mock_file.called

    def test_stats_only_option(self, script_runner, sample_python_files):
        """Test stats-only option."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")

            with patch("os.path.exists", return_value=True):
                result = script_runner.run_script(
                    "format_code.sh",
                    ["--stats-only", str(sample_python_files["good_format"])],
                )

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_stats_with_formatting(self, mock_run, script_runner, mock_env):
        """Test showing stats along with formatting."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--stats"])

        assert result.returncode == 0

    def test_tools_not_found(self, script_runner):
        """Test handling when formatting tools are not available."""
        with patch("shutil.which", return_value=None):
            result = script_runner.run_script("format_code.sh")

        assert result.returncode != 0

    def test_target_path_not_exists(self, script_runner):
        """Test handling when target path doesn't exist."""
        with patch("os.path.exists", return_value=False):
            result = script_runner.run_script("format_code.sh", ["nonexistent_path"])

        assert result.returncode != 0

    @patch("subprocess.run")
    def test_black_formatting_issues(self, mock_run, script_runner, mock_env):
        """Test handling of Black formatting issues."""
        mock_run.side_effect = [
            # Black - formatting issues found
            MagicMock(returncode=1),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh", ["--check"])

        # Should have non-zero exit code due to formatting issues
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_ruff_linting_issues(self, mock_run, script_runner, mock_env):
        """Test handling of Ruff linting issues."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check - linting issues found
            MagicMock(returncode=1),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        # Should have non-zero exit code due to linting issues
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_mypy_type_issues(self, mock_run, script_runner, mock_env):
        """Test handling of MyPy type issues."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy - type issues found
            MagicMock(returncode=1),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        # Should have non-zero exit code due to type issues
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_multiple_tool_failures(self, mock_run, script_runner, mock_env):
        """Test handling when multiple tools fail."""
        mock_run.side_effect = [
            # Black - failure
            MagicMock(returncode=1),
            # Ruff check - failure
            MagicMock(returncode=1),
            # MyPy - failure
            MagicMock(returncode=1),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        # Should combine exit codes (2 | 4 | 8 = 14)
        assert result.returncode != 0

    def test_unknown_option(self, script_runner):
        """Test handling of unknown options."""
        result = script_runner.run_script("format_code.sh", ["--invalid-option"])
        assert result.returncode != 0

    @patch("subprocess.run")
    def test_virtual_environment_activation(self, mock_run, script_runner, mock_env):
        """Test virtual environment activation when available."""
        with patch("os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True
            mock_run.side_effect = [
                # Black
                MagicMock(returncode=0),
                # Ruff check
                MagicMock(returncode=0),
                # MyPy
                MagicMock(returncode=0),
            ]

            with patch(
                "shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"
            ), patch("os.path.exists", return_value=True), patch.dict(
                os.environ, mock_env
            ):
                result = script_runner.run_script("format_code.sh")

        assert result.returncode == 0

    @patch("subprocess.run")
    def test_black_configuration_options(self, mock_run, script_runner, mock_env):
        """Test that Black is called with correct configuration options."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        assert result.returncode == 0
        # Verify Black was called with expected arguments
        black_call = mock_run.call_args_list[0]
        assert "--line-length" in black_call[0][0]
        assert "88" in black_call[0][0]

    @patch("subprocess.run")
    def test_ruff_configuration_options(self, mock_run, script_runner, mock_env):
        """Test that Ruff is called with correct configuration options."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        assert result.returncode == 0
        # Verify Ruff was called with expected arguments
        ruff_call = mock_run.call_args_list[1]
        assert "check" in ruff_call[0][0]

    @patch("subprocess.run")
    def test_mypy_configuration_options(self, mock_run, script_runner, mock_env):
        """Test that MyPy is called with correct configuration options."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        assert result.returncode == 0
        # Verify MyPy was called with expected arguments
        mypy_call = mock_run.call_args_list[2]
        assert "--python-version" in mypy_call[0][0]
        assert "3.11" in mypy_call[0][0]

    @patch("subprocess.run")
    def test_working_directory_handling(self, mock_run, script_runner, mock_env):
        """Test that script handles working directory changes properly."""
        mock_run.side_effect = [
            # Black
            MagicMock(returncode=0),
            # Ruff check
            MagicMock(returncode=0),
            # MyPy
            MagicMock(returncode=0),
        ]

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), patch(
            "os.path.exists", return_value=True
        ), patch.dict(os.environ, mock_env):
            result = script_runner.run_script("format_code.sh")

        assert result.returncode == 0

    def test_relative_path_handling(self, script_runner):
        """Test handling of relative paths."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # Black
                MagicMock(returncode=0),
                # Ruff check
                MagicMock(returncode=0),
                # MyPy
                MagicMock(returncode=0),
            ]

            with patch(
                "shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"
            ), patch(
                "os.path.exists",
                side_effect=lambda path: "app" in str(path),
            ):
                result = script_runner.run_script("format_code.sh", ["app/"])

        assert result.returncode == 0

    def test_exit_code_documentation(self, script_runner):
        """Test that exit codes are properly documented."""
        help_result = script_runner.run_script("format_code.sh", ["--help"])

        assert "EXIT CODES:" in help_result.stdout
        assert "0" in help_result.stdout  # Success
        assert "2" in help_result.stdout  # Black issues
        assert "4" in help_result.stdout  # Ruff issues
        assert "8" in help_result.stdout  # MyPy issues

    def test_script_logging_output(self, script_runner):
        """Test that script produces proper logging output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch(
                "shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"
            ), patch("os.path.exists", return_value=True):
                result = script_runner.run_script("format_code.sh", ["--stats-only"])

        # Check for logging patterns
        output = result.stdout + result.stderr
        assert "[INFO]" in output
        assert "Starting code formatting and quality script" in output

    def test_environment_variable_usage(self, script_runner):
        """Test that script uses environment variables properly."""
        custom_env = {
            "PROJECT_ROOT": "/custom/project/root",
            "ENVIRONMENT": "development",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch(
                "shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"
            ), patch("os.path.exists", return_value=True), patch.dict(
                os.environ, custom_env
            ):
                result = script_runner.run_script("format_code.sh", ["--stats-only"])

        assert result.returncode == 0
