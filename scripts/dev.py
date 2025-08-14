#!/usr/bin/env python3
"""
Development script for DevPocket API.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command: str, description: str = None) -> int:
    """Run a shell command and return the exit code."""
    if description:
        print(f"🔄 {description}")
    
    result = subprocess.run(command, shell=True, cwd=Path(__file__).parent.parent)
    return result.returncode


def start_server():
    """Start the development server."""
    print("🚀 Starting DevPocket API development server...")
    return run_command(
        "source venv/bin/activate && python main.py",
        "Starting FastAPI server with hot reload"
    )


def install_deps():
    """Install dependencies."""
    print("📦 Installing dependencies...")
    return run_command(
        "source venv/bin/activate && pip install -r requirements.txt",
        "Installing Python dependencies"
    )


def format_code():
    """Format code with black."""
    print("🎨 Formatting code...")
    return run_command(
        "source venv/bin/activate && black .",
        "Running black formatter"
    )


def lint_code():
    """Lint code with ruff."""
    print("🔍 Linting code...")
    return run_command(
        "source venv/bin/activate && ruff check .",
        "Running ruff linter"
    )


def type_check():
    """Type check with mypy."""
    print("🏷️ Type checking...")
    return run_command(
        "source venv/bin/activate && mypy app/",
        "Running mypy type checker"
    )


def run_tests():
    """Run tests with pytest."""
    print("🧪 Running tests...")
    return run_command(
        "source venv/bin/activate && python -m pytest tests/ -v",
        "Running pytest"
    )


def check_all():
    """Run all checks (format, lint, type check, tests)."""
    print("✅ Running all checks...")
    
    checks = [
        ("Format code", format_code),
        ("Lint code", lint_code),
        ("Type check", type_check),
        ("Run tests", run_tests),
    ]
    
    failed = []
    
    for check_name, check_func in checks:
        if check_func() != 0:
            failed.append(check_name)
    
    if failed:
        print(f"\n❌ Failed checks: {', '.join(failed)}")
        return 1
    else:
        print("\n✅ All checks passed!")
        return 0


def create_env():
    """Create .env file from template."""
    env_file = Path(__file__).parent.parent / ".env"
    env_example = Path(__file__).parent.parent / ".env.example"
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        return 0
    
    if not env_example.exists():
        print("❌ .env.example file not found")
        return 1
    
    try:
        env_content = env_example.read_text()
        env_file.write_text(env_content)
        print("✅ Created .env file from .env.example")
        print("⚠️  Please update the values in .env file for your environment")
        return 0
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return 1


def setup_db():
    """Set up database."""
    print("🗄️ Setting up database...")
    print("⚠️  Make sure PostgreSQL is running and database exists")
    
    # This will be implemented when we add Alembic migrations
    commands = [
        "source venv/bin/activate && alembic upgrade head",
    ]
    
    for cmd in commands:
        if run_command(cmd, f"Running: {cmd}") != 0:
            return 1
    
    return 0


def clean():
    """Clean up generated files."""
    print("🧹 Cleaning up...")
    
    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov/",
    ]
    
    for pattern in patterns:
        run_command(f"find . -path '{pattern}' -delete", f"Removing {pattern}")
    
    print("✅ Cleanup complete")
    return 0


def show_help():
    """Show help message."""
    print("""
🔧 DevPocket API Development Script

Usage: python scripts/dev.py <command>

Commands:
  start      Start the development server
  install    Install dependencies
  format     Format code with black
  lint       Lint code with ruff
  typecheck  Type check with mypy
  test       Run tests with pytest
  check      Run all checks (format, lint, typecheck, test)
  env        Create .env file from template
  db         Set up database
  clean      Clean up generated files
  help       Show this help message

Examples:
  python scripts/dev.py start
  python scripts/dev.py check
  python scripts/dev.py install
""")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_help()
        return 0
    
    command = sys.argv[1].lower()
    
    commands = {
        "start": start_server,
        "install": install_deps,
        "format": format_code,
        "lint": lint_code,
        "typecheck": type_check,
        "test": run_tests,
        "check": check_all,
        "env": create_env,
        "db": setup_db,
        "clean": clean,
        "help": show_help,
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        show_help()
        return 1
    
    return commands[command]()


if __name__ == "__main__":
    sys.exit(main())