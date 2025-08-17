#!/usr/bin/env python3
"""
DevPocket API Setup Script
Automated environment setup and initialization for development and production.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


class DevPocketSetup:
    """Main setup class for DevPocket API environment."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.requirements_file = self.project_root / "requirements.txt"
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"

    def log(self, message: str, level: str = "INFO") -> None:
        """Log setup messages with timestamp."""
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_command(
        self, command: str, cwd: Path | None = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run shell command with error handling."""
        try:
            self.log(f"Running: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=check,
            )
            if result.stdout:
                self.log(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", "ERROR")
            self.log(f"Error output: {e.stderr}", "ERROR")
            raise

    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        version = sys.version_info
        if version.major != 3 or version.minor < 11:
            self.log(
                f"Python 3.11+ required, found {version.major}.{version.minor}",
                "ERROR",
            )
            return False
        self.log(
            f"Python version {version.major}.{version.minor}.{version.micro} is compatible"
        )
        return True

    def check_system_dependencies(self) -> bool:
        """Check if required system dependencies are available."""
        dependencies = ["curl", "pg_isready"]
        missing = []

        for dep in dependencies:
            try:
                subprocess.run(["which", dep], check=True, capture_output=True)
                self.log(f"System dependency '{dep}' found")
            except subprocess.CalledProcessError:
                missing.append(dep)

        if missing:
            self.log(f"Missing system dependencies: {', '.join(missing)}", "ERROR")
            self.log(
                "Please install the missing dependencies and try again",
                "ERROR",
            )
            return False

        return True

    def create_virtual_environment(self) -> bool:
        """Create Python virtual environment."""
        if self.venv_path.exists():
            self.log("Virtual environment already exists")
            return True

        try:
            self.log("Creating virtual environment...")
            self.run_command(f"{sys.executable} -m venv {self.venv_path}")
            self.log("Virtual environment created successfully")
            return True
        except Exception as e:
            self.log(f"Failed to create virtual environment: {e}", "ERROR")
            return False

    def install_requirements(self) -> bool:
        """Install Python requirements in virtual environment."""
        if not self.requirements_file.exists():
            self.log("requirements.txt not found", "ERROR")
            return False

        try:
            pip_path = self.venv_path / "bin" / "pip"
            if not pip_path.exists():
                pip_path = self.venv_path / "Scripts" / "pip.exe"  # Windows

            self.log("Installing Python requirements...")
            self.run_command(f"{pip_path} install --upgrade pip")
            self.run_command(f"{pip_path} install -r {self.requirements_file}")
            self.log("Requirements installed successfully")
            return True
        except Exception as e:
            self.log(f"Failed to install requirements: {e}", "ERROR")
            return False

    def setup_environment_file(self) -> bool:
        """Create .env file from .env.example if it doesn't exist."""
        if self.env_file.exists():
            self.log(".env file already exists")
            return True

        if not self.env_example.exists():
            self.log(".env.example not found", "ERROR")
            return False

        try:
            self.log("Creating .env file from .env.example...")
            shutil.copy2(self.env_example, self.env_file)

            # Generate a secure JWT secret key
            import secrets

            jwt_secret = secrets.token_hex(32)

            # Replace placeholder JWT secret in .env file
            with open(self.env_file) as f:
                content = f.read()

            content = content.replace(
                "your-super-secret-jwt-key-here-change-this-in-production-32-chars-minimum",
                jwt_secret,
            )

            with open(self.env_file, "w") as f:
                f.write(content)

            self.log("Environment file created with secure JWT secret")
            self.log(
                "IMPORTANT: Please review and customize the .env file for your environment",
                "WARNING",
            )
            return True
        except Exception as e:
            self.log(f"Failed to setup environment file: {e}", "ERROR")
            return False

    def check_database_connection(self) -> bool:
        """Check if database is accessible."""
        try:
            self.log("Checking database connection...")
            # Try to connect using environment variables
            from app.core.config import settings

            # Simple connection test
            test_command = f"pg_isready -h {settings.database_host} -p {settings.database_port} -U {settings.database_user}"
            result = self.run_command(test_command, check=False)

            if result.returncode == 0:
                self.log("Database connection successful")
                return True
            else:
                self.log(
                    "Database connection failed - this is normal if database is not running",
                    "WARNING",
                )
                return False
        except Exception as e:
            self.log(f"Database connection check failed: {e}", "WARNING")
            return False

    def run_database_migrations(self) -> bool:
        """Run Alembic database migrations."""
        try:
            self.log("Running database migrations...")
            python_path = self.venv_path / "bin" / "python"
            if not python_path.exists():
                python_path = self.venv_path / "Scripts" / "python.exe"  # Windows

            self.run_command(f"{python_path} -m alembic upgrade head")
            self.log("Database migrations completed successfully")
            return True
        except Exception as e:
            self.log(f"Database migrations failed: {e}", "WARNING")
            self.log("This is normal if database is not running", "WARNING")
            return False

    def validate_installation(self) -> bool:
        """Validate the installation by importing main modules."""
        try:
            self.log("Validating installation...")
            python_path = self.venv_path / "bin" / "python"
            if not python_path.exists():
                python_path = self.venv_path / "Scripts" / "python.exe"  # Windows

            # Create a temporary test script file
            test_file = self.project_root / "test_import.py"
            test_script = """import sys
sys.path.insert(0, '.')
try:
    from app.core.config import settings
    from main import app
    print("Application imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)
"""
            with open(test_file, "w") as f:
                f.write(test_script)

            try:
                self.run_command(f"{python_path} {test_file}")
                self.log("Installation validation completed successfully")
                return True
            finally:
                # Clean up test file
                if test_file.exists():
                    test_file.unlink()
        except Exception as e:
            self.log(f"Installation validation failed: {e}", "ERROR")
            return False

    def setup_development_environment(self) -> bool:
        """Complete development environment setup."""
        self.log("=== DevPocket API Development Environment Setup ===")

        steps = [
            ("Checking Python version", self.check_python_version),
            ("Checking system dependencies", self.check_system_dependencies),
            ("Creating virtual environment", self.create_virtual_environment),
            ("Installing requirements", self.install_requirements),
            ("Setting up environment file", self.setup_environment_file),
            ("Validating installation", self.validate_installation),
        ]

        for step_name, step_func in steps:
            self.log(f"Step: {step_name}")
            if not step_func():
                self.log(f"Setup failed at step: {step_name}", "ERROR")
                return False

        # Optional steps (don't fail setup if they fail)
        self.check_database_connection()
        self.run_database_migrations()

        self.log("=== Development Environment Setup Complete ===")
        self.print_next_steps()
        return True

    def print_next_steps(self) -> None:
        """Print instructions for next steps."""
        print("\n" + "=" * 60)
        print("DevPocket API setup completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("\n1. Activate the virtual environment:")
        print("   source venv/bin/activate  # Linux/macOS")
        print("   venv\\Scripts\\activate     # Windows")
        print("\n2. Review and customize your environment:")
        print("   edit .env")
        print("\n3. Start the development server:")
        print("   python main.py")
        print("   # OR")
        print("   uvicorn main:app --reload")
        print("\n4. Access the API documentation:")
        print("   http://localhost:8000/docs")
        print("\n5. Run tests:")
        print("   pytest")
        print("\n6. Use Docker for full environment:")
        print("   docker-compose up -d")
        print("\nFor more information, see README.md")
        print("=" * 60)


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="DevPocket API Setup Script")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip installation validation step",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    setup = DevPocketSetup(project_root=args.project_root)

    try:
        success = setup.setup_development_environment()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        setup.log("Setup interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        setup.log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
