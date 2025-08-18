"""
Command factory for testing.
"""

import json
from datetime import UTC, datetime, timedelta

import factory
from factory import fuzzy
from faker import Faker

from app.models.command import Command

fake = Faker()


class CommandFactory(factory.Factory):
    """Factory for Command model."""

    class Meta:
        model = Command

    # Foreign key (will be set by tests)
    session_id = factory.LazyAttribute(lambda obj: str(fake.uuid4()))

    # Command details
    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "ls -la",
                "cd /home/user",
                "git status",
                "npm install",
                "docker ps",
                "ps aux",
                "cat /etc/passwd",
                "top",
                "tail -f /var/log/nginx/access.log",
                "find . -name '*.py'",
                "curl -s https://api.github.com/user",
                "python manage.py migrate",
                "grep -r 'TODO' .",
                "chmod +x script.sh",
                "sudo systemctl restart nginx",
            ]
        )
    )

    # Command execution results
    output = factory.LazyAttribute(lambda obj: _generate_command_output(obj.command))
    error_output = None
    exit_code = 0
    stdout = factory.SelfAttribute("output")  # Alias for output  
    stderr = factory.SelfAttribute("error_output")  # Alias for error_output

    # Command status
    status = "success"

    # Execution timing
    started_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(seconds=5))
    completed_at = factory.LazyFunction(
        lambda: datetime.now(UTC) - timedelta(seconds=1)
    )
    execution_time = factory.LazyAttribute(
        lambda obj: (
            (obj.completed_at - obj.started_at).total_seconds()
            if obj.started_at and obj.completed_at
            else None
        )
    )
    executed_at = factory.SelfAttribute("started_at")  # Alias for started_at

    # Command metadata
    working_directory = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "/home/user",
                "/var/www/html",
                "/opt/app",
                "/tmp",
                "/usr/local/bin",
            ]
        )
    )
    environment_vars = factory.LazyFunction(
        lambda: json.dumps(
            {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": "/home/user",
                "USER": "user",
                "SHELL": "/bin/bash",
            }
        )
    )

    # AI-related fields
    was_ai_suggested = False
    ai_explanation = None

    # Command classification
    command_type = factory.LazyAttribute(lambda obj: _classify_command(obj.command))

    # Security flags
    is_sensitive = factory.LazyAttribute(lambda obj: _check_sensitive(obj.command))


class SuccessfulCommandFactory(CommandFactory):
    """Factory for successful Command."""

    exit_code = 0
    status = "success"
    error_output = None


class FailedCommandFactory(CommandFactory):
    """Factory for failed Command."""

    exit_code = fuzzy.FuzzyInteger(1, 255)
    status = "error"
    error_output = factory.LazyAttribute(
        lambda obj: _generate_error_output(obj.command)
    )
    output = None


class RunningCommandFactory(CommandFactory):
    """Factory for currently running Command."""

    status = "running"
    started_at = factory.LazyFunction(datetime.utcnow)
    completed_at = None
    execution_time = None
    exit_code = None


class PendingCommandFactory(CommandFactory):
    """Factory for pending Command."""

    status = "pending"
    started_at = None
    completed_at = None
    execution_time = None
    exit_code = None
    output = None


class CancelledCommandFactory(CommandFactory):
    """Factory for cancelled Command."""

    status = "cancelled"
    started_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(seconds=2))
    completed_at = factory.LazyFunction(datetime.utcnow)
    execution_time = factory.LazyAttribute(
        lambda obj: (obj.completed_at - obj.started_at).total_seconds()
    )
    exit_code = None
    output = None


class TimeoutCommandFactory(CommandFactory):
    """Factory for timed out Command."""

    status = "timeout"
    started_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(minutes=5))
    completed_at = factory.LazyFunction(datetime.utcnow)
    execution_time = 300.0  # 5 minutes
    exit_code = None
    output = "Command timed out after 300 seconds"


class AISuggestedCommandFactory(CommandFactory):
    """Factory for AI-suggested Command."""

    was_ai_suggested = True
    ai_explanation = factory.LazyAttribute(lambda obj: f"AI suggested: {obj.command}")
    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "git add . && git commit -m 'Update files'",
                "find . -name '*.log' -delete",
                "docker-compose up -d",
                "systemctl status nginx",
                "tail -n 100 /var/log/syslog",
            ]
        )
    )


class GitCommandFactory(CommandFactory):
    """Factory for Git commands."""

    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "git status",
                "git add .",
                "git commit -m 'Update code'",
                "git push origin main",
                "git pull",
                "git branch",
                "git checkout -b feature/new-feature",
                "git merge develop",
                "git log --oneline",
            ]
        )
    )
    command_type = "git"
    working_directory = factory.LazyFunction(
        lambda: fake.random_element(
            ["/home/user/project", "/var/www/app", "/opt/development/repo"]
        )
    )


class FileOperationCommandFactory(CommandFactory):
    """Factory for file operation commands."""

    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "ls -la",
                "cd /home/user",
                "mkdir -p new/directory",
                "rm -rf temp/",
                "cp file.txt backup/",
                "mv old_file.txt new_file.txt",
                "find . -name '*.py'",
                "chmod +x script.sh",
                "chown user:group file.txt",
            ]
        )
    )
    command_type = "file_operation"


class NetworkCommandFactory(CommandFactory):
    """Factory for network commands."""

    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "ping google.com",
                "curl -s https://api.github.com/user",
                "wget https://example.com/file.zip",
                "ssh user@remote-server",
                "scp file.txt user@server:/home/",
                "netstat -tulpn",
                "nmap -p 80,443 example.com",
            ]
        )
    )
    command_type = "network"


class SystemCommandFactory(CommandFactory):
    """Factory for system commands."""

    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "ps aux",
                "top",
                "htop",
                "kill -9 1234",
                "systemctl restart nginx",
                "service apache2 status",
                "df -h",
                "du -sh /var/log",
                "mount /dev/sdb1 /mnt",
            ]
        )
    )
    command_type = "system"


class SensitiveCommandFactory(CommandFactory):
    """Factory for sensitive commands."""

    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "echo 'password123' | sudo -S apt update",
                "ssh-keygen -t rsa -b 4096",
                "export API_KEY=secret_key_here",
                "mysql -u root -p'secret_password' database",
                "curl -H 'Authorization: Bearer token123' api.example.com",
            ]
        )
    )
    is_sensitive = True


class LongRunningCommandFactory(CommandFactory):
    """Factory for long-running commands."""

    command = factory.LazyFunction(
        lambda: fake.random_element(
            [
                "rsync -av /large/directory/ /backup/",
                "tar -czf backup.tar.gz /home/user/",
                "docker build -t myapp .",
                "npm install",
                "apt update && apt upgrade -y",
            ]
        )
    )
    execution_time = fuzzy.FuzzyFloat(30.0, 300.0)  # 30 seconds to 5 minutes
    started_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(minutes=2))
    completed_at = factory.LazyAttribute(
        lambda obj: obj.started_at + timedelta(seconds=obj.execution_time)
    )


# Helper functions for generating realistic test data
def _generate_command_output(command: str) -> str:
    """Generate realistic output for a command."""
    if command.startswith("ls"):
        return "file1.txt\nfile2.py\ndirectory/\n.hidden_file"
    elif command.startswith("git status"):
        return "On branch main\nYour branch is up to date with 'origin/main'.\n\nnothing to commit, working tree clean"
    elif command.startswith("ps"):
        return "PID TTY          TIME CMD\n1234 pts/0    00:00:01 bash\n5678 pts/0    00:00:00 ps"
    elif command.startswith("curl"):
        return '{"status": "success", "data": {"key": "value"}}'
    elif command.startswith("ping"):
        return "PING google.com (8.8.8.8) 56(84) bytes of data.\n64 bytes from 8.8.8.8: icmp_seq=1 time=10.2 ms"
    else:
        return fake.text(max_nb_chars=200)


def _generate_error_output(command: str) -> str:
    """Generate realistic error output for a command."""
    if command.startswith("ls"):
        return "ls: cannot access 'nonexistent': No such file or directory"
    elif command.startswith("git"):
        return "fatal: not a git repository (or any of the parent directories): .git"
    elif command.startswith("curl"):
        return "curl: (6) Could not resolve host: invalid-domain.com"
    else:
        return fake.random_element(
            [
                "Permission denied",
                "Command not found",
                "No such file or directory",
                "Connection refused",
                "Operation not permitted",
            ]
        )


def _classify_command(command: str) -> str:
    """Classify command type."""
    command_lower = command.lower().strip()

    if command_lower.startswith(("git ", "gh ")):
        return "git"
    elif any(
        command_lower.startswith(cmd)
        for cmd in ["ls", "cd", "mkdir", "rm", "cp", "mv", "find"]
    ):
        return "file_operation"
    elif any(
        command_lower.startswith(cmd) for cmd in ["ping", "curl", "wget", "ssh", "scp"]
    ):
        return "network"
    elif any(
        command_lower.startswith(cmd)
        for cmd in ["ps", "top", "kill", "systemctl", "service"]
    ):
        return "system"
    elif any(
        command_lower.startswith(cmd) for cmd in ["docker", "kubectl", "python", "node"]
    ):
        return "development"
    else:
        return "other"


def _check_sensitive(command: str) -> bool:
    """Check if command contains sensitive information."""
    sensitive_patterns = [
        "password",
        "secret",
        "key",
        "token",
        "auth",
        "credential",
    ]
    return any(pattern in command.lower() for pattern in sensitive_patterns)
