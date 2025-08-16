"""
Pytest configuration and fixtures for script testing.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
from typing import Generator, Dict


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def scripts_dir(project_root: Path) -> Path:
    """Get the scripts directory."""
    return project_root / "scripts"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def mock_env() -> Generator[Dict[str, str], None, None]:
    """Mock environment variables for testing."""
    test_env = {
        "ENVIRONMENT": "test",
        "TESTING": "true",
        "DATABASE_URL": "postgresql://test:test@localhost:5433/devpocket_test",
        "REDIS_URL": "redis://localhost:6380",
        "PROJECT_ROOT": str(Path(__file__).parent.parent.parent),
    }

    with patch.dict(os.environ, test_env, clear=False):
        yield test_env


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for testing."""
    with patch("subprocess.run") as mock_run, patch(
        "subprocess.Popen"
    ) as mock_popen, patch("subprocess.check_output") as mock_output:
        # Default successful return
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_output.return_value = b"test output"

        # Mock Popen for interactive processes
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout.read.return_value = b"test output"
        mock_process.stderr.read.return_value = b""
        mock_process.communicate.return_value = (b"test output", b"")
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        yield {
            "run": mock_run,
            "popen": mock_popen,
            "check_output": mock_output,
            "process": mock_process,
        }


@pytest.fixture
def script_runner():
    """Utility for running shell scripts in tests."""

    class ScriptRunner:
        def __init__(self):
            self.project_root = Path(__file__).parent.parent.parent
            self.scripts_dir = self.project_root / "scripts"

        def run_script(
            self,
            script_name: str,
            args: list = None,
            env: Dict[str, str] = None,
            capture_output: bool = True,
            timeout: int = 30,
        ) -> subprocess.CompletedProcess:
            """
            Run a shell script with given arguments.

            Args:
                script_name: Name of the script file (e.g., 'db_migrate.sh')
                args: List of arguments to pass to the script
                env: Environment variables to set
                capture_output: Whether to capture stdout/stderr
                timeout: Timeout in seconds

            Returns:
                CompletedProcess object with results
            """
            script_path = self.scripts_dir / script_name

            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")

            # Make script executable
            script_path.chmod(0o755)

            cmd = [str(script_path)]
            if args:
                cmd.extend(args)

            # Set up environment
            test_env = os.environ.copy()
            if env:
                test_env.update(env)

            return subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                env=test_env,
                timeout=timeout,
                cwd=str(self.project_root),
            )

        def get_script_help(self, script_name: str) -> str:
            """Get help text from a script."""
            try:
                result = self.run_script(script_name, ["--help"])
                return result.stdout
            except subprocess.CalledProcessError as e:
                return e.stdout or e.stderr or ""

        def check_script_syntax(self, script_name: str) -> bool:
            """Check if script has valid bash syntax."""
            script_path = self.scripts_dir / script_name
            try:
                subprocess.run(
                    ["bash", "-n", str(script_path)],
                    check=True,
                    capture_output=True,
                )
                return True
            except subprocess.CalledProcessError:
                return False

        def is_script_executable(self, script_name: str) -> bool:
            """Check if script is executable."""
            script_path = self.scripts_dir / script_name
            return os.access(script_path, os.X_OK)

    return ScriptRunner()


@pytest.fixture
def mock_database():
    """Mock database operations for testing."""

    class MockDatabase:
        def __init__(self):
            self.connection_success = True
            self.migration_status = "current"
            self.health_status = "healthy"
            self.tables = [
                "users",
                "ssh_profiles",
                "commands",
                "sessions",
                "sync_data",
            ]

        async def test_connection(self):
            if self.connection_success:
                return True
            raise Exception("Database connection failed")

        async def get_migration_status(self):
            return self.migration_status

        async def run_migration(self, target="head"):
            if target == "invalid":
                raise Exception("Invalid migration target")
            return True

        async def get_health(self):
            return {
                "status": self.health_status,
                "tables": self.tables,
                "table_count": len(self.tables),
            }

        def set_connection_failure(self):
            self.connection_success = False

        def set_migration_failure(self):
            self.migration_status = "error"

        def set_unhealthy(self):
            self.health_status = "unhealthy"

    return MockDatabase()


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing."""

    class MockFileOps:
        def __init__(self):
            self.files_created = []
            self.files_deleted = []
            self.temp_scripts = {}

        def create_temp_file(self, content: str, suffix: str = ".py") -> str:
            """Create a temporary file with given content."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=suffix, delete=False
            ) as f:
                f.write(content)
                temp_file = f.name

            self.files_created.append(temp_file)
            return temp_file

        def cleanup(self):
            """Clean up temporary files."""
            for file_path in self.files_created:
                try:
                    os.unlink(file_path)
                except FileNotFoundError:
                    pass
            self.files_created.clear()

    mock_ops = MockFileOps()
    yield mock_ops
    mock_ops.cleanup()


@pytest.fixture
def sample_python_files(temp_dir: Path):
    """Create sample Python files for formatting tests."""
    files = {}

    # Create a sample Python file with formatting issues
    bad_file = temp_dir / "bad_format.py"
    bad_file.write_text(
        """
# Bad formatting example
import os,sys
import json


def   badly_formatted_function(  x,y  ):
    if x>y:
        return x+y
    else:
        return x-y


class   BadlyFormattedClass:
    def __init__(self,value):
        self.value=value
    
    def get_value(self):
        return self.value


# Missing type hints and other issues
def function_without_types(data):
    result=[]
    for item in data:
        if item>0:
            result.append(item*2)
    return result
"""
    )
    files["bad_format"] = bad_file

    # Create a well-formatted file
    good_file = temp_dir / "good_format.py"
    good_file.write_text(
        '''
"""
Well-formatted Python file example.
"""

import json
import os
import sys
from typing import List


def well_formatted_function(x: int, y: int) -> int:
    """A well-formatted function."""
    if x > y:
        return x + y
    else:
        return x - y


class WellFormattedClass:
    """A well-formatted class."""
    
    def __init__(self, value: int) -> None:
        self.value = value
    
    def get_value(self) -> int:
        """Get the stored value."""
        return self.value


def function_with_types(data: List[int]) -> List[int]:
    """Function with proper type hints."""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
'''
    )
    files["good_format"] = good_file

    return files


@pytest.fixture(autouse=True)
def preserve_working_directory():
    """Preserve the current working directory."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)


class ScriptTestError(Exception):
    """Custom exception for script test errors."""

    pass


@pytest.fixture
def script_assertions():
    """Utility functions for script test assertions."""

    class ScriptAssertions:
        @staticmethod
        def assert_script_success(
            result: subprocess.CompletedProcess,
            message: str = "Script should succeed",
        ):
            """Assert that a script ran successfully."""
            if result.returncode != 0:
                raise AssertionError(
                    f"{message}. Exit code: {result.returncode}, "
                    f"stdout: {result.stdout}, stderr: {result.stderr}"
                )

        @staticmethod
        def assert_script_failure(
            result: subprocess.CompletedProcess,
            expected_code: int = None,
            message: str = "Script should fail",
        ):
            """Assert that a script failed with expected exit code."""
            if result.returncode == 0:
                raise AssertionError(f"{message}. Script unexpectedly succeeded.")

            if expected_code is not None and result.returncode != expected_code:
                raise AssertionError(
                    f"{message}. Expected exit code {expected_code}, "
                    f"got {result.returncode}"
                )

        @staticmethod
        def assert_contains_log_message(output: str, level: str, message: str):
            """Assert that output contains a specific log message."""
            expected_pattern = f"[{level}]"
            if expected_pattern not in output or message not in output:
                raise AssertionError(
                    f"Expected log message with level '{level}' containing '{message}' "
                    f"not found in output: {output}"
                )

        @staticmethod
        def assert_file_exists(file_path: Path, message: str = None):
            """Assert that a file exists."""
            if not file_path.exists():
                msg = message or f"File should exist: {file_path}"
                raise AssertionError(msg)

        @staticmethod
        def assert_file_not_exists(file_path: Path, message: str = None):
            """Assert that a file does not exist."""
            if file_path.exists():
                msg = message or f"File should not exist: {file_path}"
                raise AssertionError(msg)

    return ScriptAssertions()
