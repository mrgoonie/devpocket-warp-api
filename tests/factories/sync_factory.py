"""
Sync data factory for testing.
"""

from datetime import datetime, timedelta, timezone
import factory
from factory import fuzzy
from faker import Faker
import json

from app.models.sync import SyncData

fake = Faker()


class SyncDataFactory(factory.Factory):
    """Factory for SyncData model."""
    
    class Meta:
        model = SyncData
    
    # Foreign key (will be set by tests)
    user_id = factory.LazyAttribute(lambda obj: str(fake.uuid4()))
    
    # Sync metadata
    sync_type = fuzzy.FuzzyChoice(["commands", "ssh_profiles", "settings", "history"])
    sync_key = factory.LazyAttribute(lambda obj: f"{obj.sync_type}_{fake.uuid4()}")
    
    # Data content (varies by sync_type)
    data = factory.LazyAttribute(lambda obj: _generate_sync_data(obj.sync_type))
    
    # Sync status
    version = fuzzy.FuzzyInteger(1, 10)
    is_deleted = False
    
    # Device information
    source_device_id = factory.LazyFunction(lambda: str(fake.uuid4()))
    source_device_type = fuzzy.FuzzyChoice(["ios", "android", "web"])
    
    # Conflict resolution
    conflict_data = None
    resolved_at = None
    
    # Sync timestamps
    synced_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(hours=1))
    last_modified_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(minutes=30))


class CommandSyncDataFactory(SyncDataFactory):
    """Factory for command sync data."""
    
    sync_type = "commands"
    sync_key = factory.Sequence(lambda n: f"commands_session_{n}")
    
    data = factory.LazyFunction(lambda: {
        "session_id": str(fake.uuid4()),
        "commands": [
            {
                "command": "ls -la",
                "output": "total 24\ndrwxr-xr-x 3 user user 4096 Jan 15 10:30 .",
                "exit_code": 0,
                "timestamp": "2025-01-15T10:30:00Z"
            },
            {
                "command": "git status",
                "output": "On branch main\nnothing to commit, working tree clean",
                "exit_code": 0,
                "timestamp": "2025-01-15T10:31:00Z"
            }
        ]
    })


class SSHProfileSyncDataFactory(SyncDataFactory):
    """Factory for SSH profile sync data."""
    
    sync_type = "ssh_profiles"
    sync_key = factory.Sequence(lambda n: f"ssh_profile_{n}")
    
    data = factory.LazyFunction(lambda: {
        "profile_id": str(fake.uuid4()),
        "name": fake.word().title() + " Server",
        "host": fake.domain_name(),
        "port": 22,
        "username": fake.user_name(),
        "auth_method": "key",
        "description": fake.text(max_nb_chars=100),
        "created_at": "2025-01-15T09:00:00Z"
    })


class SettingsSyncDataFactory(SyncDataFactory):
    """Factory for settings sync data."""
    
    sync_type = "settings"
    sync_key = factory.Sequence(lambda n: f"user_settings_{n}")
    
    data = factory.LazyFunction(lambda: {
        "terminal_theme": fake.random_element(["dark", "light", "high-contrast"]),
        "terminal_font_size": fake.random_int(min=10, max=20),
        "terminal_font_family": "Fira Code",
        "preferred_ai_model": "claude-3-haiku",
        "ai_suggestions_enabled": True,
        "sync_enabled": True,
        "custom_shortcuts": {
            "ctrl_c": "interrupt",
            "ctrl_d": "exit"
        }
    })


class HistorySyncDataFactory(SyncDataFactory):
    """Factory for history sync data."""
    
    sync_type = "history"
    sync_key = factory.Sequence(lambda n: f"command_history_{n}")
    
    data = factory.LazyFunction(lambda: {
        "commands": [
            "cd /home/user",
            "ls -la",
            "git pull",
            "npm install",
            "npm start"
        ],
        "working_directory": "/home/user/project",
        "session_duration": 3600,
        "last_activity": "2025-01-15T11:00:00Z"
    })


class DeletedSyncDataFactory(SyncDataFactory):
    """Factory for deleted sync data."""
    
    is_deleted = True
    data = factory.LazyFunction(lambda: {})  # Empty data for deleted items


class ConflictedSyncDataFactory(SyncDataFactory):
    """Factory for sync data with conflicts."""
    
    conflict_data = factory.LazyFunction(lambda: {
        "current_data": {
            "terminal_theme": "dark",
            "font_size": 14
        },
        "conflicting_data": {
            "terminal_theme": "light",
            "font_size": 16
        },
        "conflict_created_at": datetime.now(timezone.utc).isoformat()
    })
    
    resolved_at = None


class ResolvedConflictSyncDataFactory(ConflictedSyncDataFactory):
    """Factory for resolved conflict sync data."""
    
    resolved_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(hours=1))
    conflict_data = None


class RecentSyncDataFactory(SyncDataFactory):
    """Factory for recently synced data."""
    
    synced_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(minutes=5))
    last_modified_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(minutes=2))


class OldSyncDataFactory(SyncDataFactory):
    """Factory for old sync data."""
    
    synced_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(days=7))
    last_modified_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(days=5))
    version = fuzzy.FuzzyInteger(5, 15)


class iOSSyncDataFactory(SyncDataFactory):
    """Factory for iOS device sync data."""
    
    source_device_type = "ios"
    source_device_id = factory.LazyFunction(lambda: f"ios_device_{fake.uuid4()}")


class AndroidSyncDataFactory(SyncDataFactory):
    """Factory for Android device sync data."""
    
    source_device_type = "android"
    source_device_id = factory.LazyFunction(lambda: f"android_device_{fake.uuid4()}")


class WebSyncDataFactory(SyncDataFactory):
    """Factory for web device sync data."""
    
    source_device_type = "web"
    source_device_id = factory.LazyFunction(lambda: f"web_session_{fake.uuid4()}")


class HighVersionSyncDataFactory(SyncDataFactory):
    """Factory for high version sync data (frequently updated)."""
    
    version = fuzzy.FuzzyInteger(10, 50)
    last_modified_at = factory.LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(minutes=1))


# Helper function to generate appropriate sync data based on type
def _generate_sync_data(sync_type: str) -> dict:
    """Generate appropriate sync data based on sync type."""
    
    if sync_type == "commands":
        return {
            "session_id": str(fake.uuid4()),
            "commands": [
                {
                    "command": fake.random_element([
                        "ls -la", "git status", "npm install", "docker ps", "ps aux"
                    ]),
                    "output": fake.text(max_nb_chars=100),
                    "exit_code": fake.random_element([0, 1]),
                    "timestamp": fake.date_time_between(
                        start_date="-1d", end_date="now"
                    ).isoformat() + "Z"
                }
                for _ in range(fake.random_int(min=1, max=5))
            ],
            "session_duration": fake.random_int(min=60, max=3600)
        }
    
    elif sync_type == "ssh_profiles":
        return {
            "profile_id": str(fake.uuid4()),
            "name": fake.word().title() + " Server",
            "host": fake.domain_name(),
            "port": fake.random_element([22, 2222, 8022]),
            "username": fake.user_name(),
            "auth_method": fake.random_element(["key", "password", "agent"]),
            "description": fake.text(max_nb_chars=100),
            "connection_count": fake.random_int(min=0, max=100),
            "last_used": fake.date_time_between(
                start_date="-30d", end_date="now"
            ).isoformat() + "Z"
        }
    
    elif sync_type == "settings":
        return {
            "terminal_theme": fake.random_element(["dark", "light", "high-contrast"]),
            "terminal_font_size": fake.random_int(min=10, max=20),
            "terminal_font_family": fake.random_element([
                "Fira Code", "Monaco", "Consolas", "Ubuntu Mono"
            ]),
            "preferred_ai_model": fake.random_element([
                "claude-3-haiku", "claude-3-sonnet", "gpt-3.5-turbo", "gpt-4"
            ]),
            "ai_suggestions_enabled": fake.boolean(),
            "sync_enabled": fake.boolean(),
            "custom_settings": {
                "notifications": fake.boolean(),
                "auto_save": fake.boolean(),
                "sound_effects": fake.boolean()
            }
        }
    
    elif sync_type == "history":
        return {
            "commands": [
                fake.random_element([
                    "cd /home/user", "ls -la", "git pull", "npm install",
                    "docker-compose up", "systemctl status nginx", "top",
                    "tail -f /var/log/nginx/access.log"
                ])
                for _ in range(fake.random_int(min=5, max=20))
            ],
            "working_directory": fake.random_element([
                "/home/user", "/var/www/html", "/opt/app", "/tmp"
            ]),
            "session_count": fake.random_int(min=1, max=10),
            "total_commands": fake.random_int(min=10, max=500),
            "last_activity": fake.date_time_between(
                start_date="-7d", end_date="now"
            ).isoformat() + "Z"
        }
    
    else:
        return {
            "type": sync_type,
            "data": fake.text(max_nb_chars=200),
            "metadata": {
                "created_by": fake.user_name(),
                "created_at": fake.date_time_between(
                    start_date="-30d", end_date="now"
                ).isoformat() + "Z"
            }
        }