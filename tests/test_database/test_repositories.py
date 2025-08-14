"""
Test repository CRUD operations and business logic.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User, UserSettings
from app.models.session import Session
from app.models.ssh_profile import SSHProfile, SSHKey
from app.models.command import Command
from app.models.sync import SyncData
from app.repositories.user import UserRepository
from app.repositories.session import SessionRepository
from app.repositories.ssh_profile import SSHProfileRepository
from app.repositories.command import CommandRepository
from app.repositories.sync import SyncRepository
from tests.factories import (
    UserFactory, SessionFactory, SSHProfileFactory, 
    SSHKeyFactory, CommandFactory, SyncDataFactory
)


@pytest.mark.database
@pytest.mark.unit
class TestUserRepository:
    """Test UserRepository CRUD operations."""
    
    async def test_create_user(self, test_session):
        """Test user creation."""
        repo = UserRepository(test_session)
        
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hashed_password",
            "display_name": "Test User"
        }
        
        user = await repo.create(user_data)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.display_name == "Test User"
        assert user.is_active is True
        assert user.is_verified is False
    
    async def test_get_user_by_id(self, test_session):
        """Test getting user by ID."""
        repo = UserRepository(test_session)
        
        # Create user
        user = await repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Get user by ID
        found_user = await repo.get_by_id(user.id)
        
        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == "test@example.com"
    
    async def test_get_user_by_email(self, test_session):
        """Test getting user by email."""
        repo = UserRepository(test_session)
        
        # Create user
        await repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Get user by email
        found_user = await repo.get_by_email("test@example.com")
        
        assert found_user is not None
        assert found_user.email == "test@example.com"
        assert found_user.username == "testuser"
    
    async def test_get_user_by_username(self, test_session):
        """Test getting user by username."""
        repo = UserRepository(test_session)
        
        # Create user
        await repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Get user by username
        found_user = await repo.get_by_username("testuser")
        
        assert found_user is not None
        assert found_user.email == "test@example.com"
        assert found_user.username == "testuser"
    
    async def test_update_user(self, test_session):
        """Test user update."""
        repo = UserRepository(test_session)
        
        # Create user
        user = await repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Update user
        update_data = {
            "display_name": "Updated Name",
            "bio": "Updated bio",
            "timezone": "US/Pacific"
        }
        
        updated_user = await repo.update(user.id, update_data)
        
        assert updated_user.display_name == "Updated Name"
        assert updated_user.bio == "Updated bio"
        assert updated_user.timezone == "US/Pacific"
        assert updated_user.email == "test@example.com"  # Unchanged
    
    async def test_delete_user(self, test_session):
        """Test user deletion."""
        repo = UserRepository(test_session)
        
        # Create user
        user = await repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        user_id = user.id
        
        # Delete user
        success = await repo.delete(user_id)
        
        assert success is True
        
        # Verify user is deleted
        deleted_user = await repo.get_by_id(user_id)
        assert deleted_user is None
    
    async def test_list_users_with_pagination(self, test_session):
        """Test listing users with pagination."""
        repo = UserRepository(test_session)
        
        # Create multiple users
        for i in range(15):
            await repo.create({
                "email": f"user{i}@example.com",
                "username": f"user{i}",
                "password_hash": "hash"
            })
        
        # Test pagination
        page1 = await repo.list(skip=0, limit=10)
        page2 = await repo.list(skip=10, limit=10)
        
        assert len(page1) == 10
        assert len(page2) == 5
        
        # Verify no overlap
        page1_ids = {user.id for user in page1}
        page2_ids = {user.id for user in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    async def test_search_users(self, test_session):
        """Test user search functionality."""
        repo = UserRepository(test_session)
        
        # Create test users
        await repo.create({
            "email": "john.doe@example.com",
            "username": "johndoe",
            "password_hash": "hash",
            "display_name": "John Doe"
        })
        await repo.create({
            "email": "jane.smith@example.com",
            "username": "janesmith",
            "password_hash": "hash",
            "display_name": "Jane Smith"
        })
        
        # Search by username
        results = await repo.search("john")
        assert len(results) == 1
        assert results[0].username == "johndoe"
        
        # Search by email
        results = await repo.search("jane.smith")
        assert len(results) == 1
        assert results[0].email == "jane.smith@example.com"
    
    async def test_get_users_by_subscription_tier(self, test_session):
        """Test getting users by subscription tier."""
        repo = UserRepository(test_session)
        
        # Create users with different tiers
        await repo.create({
            "email": "free@example.com",
            "username": "freeuser",
            "password_hash": "hash",
            "subscription_tier": "free"
        })
        await repo.create({
            "email": "premium@example.com",
            "username": "premiumuser",
            "password_hash": "hash",
            "subscription_tier": "premium"
        })
        
        # Get premium users
        premium_users = await repo.get_by_subscription_tier("premium")
        assert len(premium_users) == 1
        assert premium_users[0].subscription_tier == "premium"
        
        # Get free users
        free_users = await repo.get_by_subscription_tier("free")
        assert len(free_users) == 1
        assert free_users[0].subscription_tier == "free"


@pytest.mark.database
@pytest.mark.unit
class TestSessionRepository:
    """Test SessionRepository CRUD operations."""
    
    async def test_create_session(self, test_session):
        """Test session creation."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        
        # Create user first
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create session
        session_data = {
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "ios",
            "device_name": "iPhone 15",
            "session_name": "Terminal Session"
        }
        
        session = await session_repo.create(session_data)
        
        assert session.id is not None
        assert session.user_id == user.id
        assert session.device_type == "ios"
        assert session.is_active is True
    
    async def test_get_active_sessions_for_user(self, test_session):
        """Test getting active sessions for a user."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create active and inactive sessions
        active_session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device1",
            "device_type": "ios",
            "is_active": True
        })
        
        inactive_session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device2",
            "device_type": "android",
            "is_active": False
        })
        
        # Get active sessions
        active_sessions = await session_repo.get_active_sessions_for_user(user.id)
        
        assert len(active_sessions) == 1
        assert active_sessions[0].id == active_session.id
        assert active_sessions[0].is_active is True
    
    async def test_end_session(self, test_session):
        """Test ending a session."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        
        # Create user and session
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web"
        })
        
        # End session
        ended_session = await session_repo.end_session(session.id)
        
        assert ended_session.is_active is False
        assert ended_session.ended_at is not None
    
    async def test_get_sessions_by_device(self, test_session):
        """Test getting sessions by device."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create sessions on different devices
        await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "ios"
        })
        await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "ios"
        })
        await session_repo.create({
            "user_id": user.id,
            "device_id": "device456",
            "device_type": "android"
        })
        
        # Get sessions for specific device
        device_sessions = await session_repo.get_sessions_by_device(
            user.id, "device123"
        )
        
        assert len(device_sessions) == 2
        for session in device_sessions:
            assert session.device_id == "device123"
    
    async def test_cleanup_old_sessions(self, test_session):
        """Test cleaning up old inactive sessions."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create old session
        old_date = datetime.utcnow() - timedelta(days=31)
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web",
            "is_active": False
        })
        
        # Manually set old date
        session.ended_at = old_date
        session.created_at = old_date
        await test_session.commit()
        
        # Create recent session
        recent_session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device456",
            "device_type": "web",
            "is_active": False
        })
        
        # Cleanup old sessions (older than 30 days)
        cleaned_count = await session_repo.cleanup_old_sessions(days=30)
        
        assert cleaned_count == 1
        
        # Verify old session is deleted
        remaining_sessions = await session_repo.get_sessions_for_user(user.id)
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].id == recent_session.id


@pytest.mark.database
@pytest.mark.unit
class TestSSHProfileRepository:
    """Test SSHProfileRepository CRUD operations."""
    
    async def test_create_ssh_profile(self, test_session):
        """Test SSH profile creation."""
        user_repo = UserRepository(test_session)
        ssh_repo = SSHProfileRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create SSH profile
        profile_data = {
            "user_id": user.id,
            "name": "Production Server",
            "host": "prod.example.com",
            "username": "deploy",
            "port": 22,
            "auth_method": "key"
        }
        
        profile = await ssh_repo.create(profile_data)
        
        assert profile.id is not None
        assert profile.name == "Production Server"
        assert profile.host == "prod.example.com"
        assert profile.port == 22
        assert profile.is_active is True
    
    async def test_get_profiles_for_user(self, test_session):
        """Test getting all profiles for a user."""
        user_repo = UserRepository(test_session)
        ssh_repo = SSHProfileRepository(test_session)
        
        # Create users
        user1 = await user_repo.create({
            "email": "user1@example.com",
            "username": "user1",
            "password_hash": "hash"
        })
        user2 = await user_repo.create({
            "email": "user2@example.com",
            "username": "user2",
            "password_hash": "hash"
        })
        
        # Create profiles for user1
        await ssh_repo.create({
            "user_id": user1.id,
            "name": "Server 1",
            "host": "server1.com",
            "username": "user"
        })
        await ssh_repo.create({
            "user_id": user1.id,
            "name": "Server 2",
            "host": "server2.com",
            "username": "user"
        })
        
        # Create profile for user2
        await ssh_repo.create({
            "user_id": user2.id,
            "name": "Server 3",
            "host": "server3.com",
            "username": "user"
        })
        
        # Get profiles for user1
        user1_profiles = await ssh_repo.get_profiles_for_user(user1.id)
        
        assert len(user1_profiles) == 2
        profile_names = {p.name for p in user1_profiles}
        assert profile_names == {"Server 1", "Server 2"}
    
    async def test_update_connection_stats(self, test_session):
        """Test updating connection statistics."""
        user_repo = UserRepository(test_session)
        ssh_repo = SSHProfileRepository(test_session)
        
        # Create user and profile
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        profile = await ssh_repo.create({
            "user_id": user.id,
            "name": "Test Server",
            "host": "test.com",
            "username": "user"
        })
        
        # Record successful connection
        updated_profile = await ssh_repo.record_connection_attempt(
            profile.id, success=True
        )
        
        assert updated_profile.connection_count == 1
        assert updated_profile.successful_connections == 1
        assert updated_profile.failed_connections == 0
        assert updated_profile.last_used_at is not None
        
        # Record failed connection
        updated_profile = await ssh_repo.record_connection_attempt(
            profile.id, success=False
        )
        
        assert updated_profile.connection_count == 2
        assert updated_profile.successful_connections == 1
        assert updated_profile.failed_connections == 1
    
    async def test_get_frequently_used_profiles(self, test_session):
        """Test getting frequently used profiles."""
        user_repo = UserRepository(test_session)
        ssh_repo = SSHProfileRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create profiles with different usage
        profile1 = await ssh_repo.create({
            "user_id": user.id,
            "name": "Frequently Used",
            "host": "freq.com",
            "username": "user",
            "connection_count": 50,
            "last_used_at": datetime.utcnow() - timedelta(hours=1)
        })
        
        profile2 = await ssh_repo.create({
            "user_id": user.id,
            "name": "Rarely Used",
            "host": "rare.com",
            "username": "user",
            "connection_count": 2,
            "last_used_at": datetime.utcnow() - timedelta(days=7)
        })
        
        # Get frequently used profiles
        frequent_profiles = await ssh_repo.get_frequently_used_profiles(
            user.id, limit=1
        )
        
        assert len(frequent_profiles) == 1
        assert frequent_profiles[0].name == "Frequently Used"


@pytest.mark.database
@pytest.mark.unit
class TestCommandRepository:
    """Test CommandRepository CRUD operations."""
    
    async def test_create_command(self, test_session):
        """Test command creation."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        command_repo = CommandRepository(test_session)
        
        # Create user and session
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web"
        })
        
        # Create command
        command_data = {
            "session_id": session.id,
            "command": "ls -la",
            "status": "pending"
        }
        
        command = await command_repo.create(command_data)
        
        assert command.id is not None
        assert command.command == "ls -la"
        assert command.status == "pending"
        assert command.session_id == session.id
    
    async def test_get_command_history(self, test_session):
        """Test getting command history for a user."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        command_repo = CommandRepository(test_session)
        
        # Create user and session
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web"
        })
        
        # Create commands
        commands = ["ls -la", "cd /home", "git status", "npm install"]
        created_commands = []
        
        for cmd in commands:
            command = await command_repo.create({
                "session_id": session.id,
                "command": cmd,
                "status": "success"
            })
            created_commands.append(command)
        
        # Get command history
        history = await command_repo.get_command_history(
            user.id, limit=3
        )
        
        assert len(history) == 3
        # Should be in reverse chronological order (newest first)
        assert history[0].command == "npm install"
        assert history[1].command == "git status"
        assert history[2].command == "cd /home"
    
    async def test_search_commands(self, test_session):
        """Test command search functionality."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        command_repo = CommandRepository(test_session)
        
        # Create user and session
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web"
        })
        
        # Create commands
        commands = [
            "git status",
            "git commit -m 'update'",
            "npm install",
            "docker ps",
            "git push origin main"
        ]
        
        for cmd in commands:
            await command_repo.create({
                "session_id": session.id,
                "command": cmd,
                "status": "success"
            })
        
        # Search for git commands
        git_commands = await command_repo.search_commands(
            user.id, query="git"
        )
        
        assert len(git_commands) == 3
        for cmd in git_commands:
            assert "git" in cmd.command
    
    async def test_get_commands_by_status(self, test_session):
        """Test getting commands by status."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        command_repo = CommandRepository(test_session)
        
        # Create user and session
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web"
        })
        
        # Create commands with different statuses
        await command_repo.create({
            "session_id": session.id,
            "command": "command1",
            "status": "success"
        })
        await command_repo.create({
            "session_id": session.id,
            "command": "command2",
            "status": "error"
        })
        await command_repo.create({
            "session_id": session.id,
            "command": "command3",
            "status": "running"
        })
        
        # Get successful commands
        successful_commands = await command_repo.get_commands_by_status(
            user.id, "success"
        )
        
        assert len(successful_commands) == 1
        assert successful_commands[0].command == "command1"
        assert successful_commands[0].status == "success"
    
    async def test_get_ai_suggested_commands(self, test_session):
        """Test getting AI-suggested commands."""
        user_repo = UserRepository(test_session)
        session_repo = SessionRepository(test_session)
        command_repo = CommandRepository(test_session)
        
        # Create user and session
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        session = await session_repo.create({
            "user_id": user.id,
            "device_id": "device123",
            "device_type": "web"
        })
        
        # Create AI-suggested and normal commands
        await command_repo.create({
            "session_id": session.id,
            "command": "ai suggested command",
            "was_ai_suggested": True,
            "ai_explanation": "AI explained this command"
        })
        await command_repo.create({
            "session_id": session.id,
            "command": "normal command",
            "was_ai_suggested": False
        })
        
        # Get AI-suggested commands
        ai_commands = await command_repo.get_ai_suggested_commands(user.id)
        
        assert len(ai_commands) == 1
        assert ai_commands[0].command == "ai suggested command"
        assert ai_commands[0].was_ai_suggested is True
        assert ai_commands[0].ai_explanation is not None


@pytest.mark.database
@pytest.mark.unit
class TestSyncRepository:
    """Test SyncRepository CRUD operations."""
    
    async def test_create_sync_data(self, test_session):
        """Test sync data creation."""
        user_repo = UserRepository(test_session)
        sync_repo = SyncRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create sync data
        sync_data = {
            "user_id": user.id,
            "sync_type": "commands",
            "sync_key": "commands_session_123",
            "data": {"commands": ["ls", "pwd"]},
            "source_device_id": "device123",
            "source_device_type": "ios"
        }
        
        created_sync = await sync_repo.create(sync_data)
        
        assert created_sync.id is not None
        assert created_sync.sync_type == "commands"
        assert created_sync.data == {"commands": ["ls", "pwd"]}
        assert created_sync.version == 1
    
    async def test_get_sync_data_for_user(self, test_session):
        """Test getting sync data for a user."""
        user_repo = UserRepository(test_session)
        sync_repo = SyncRepository(test_session)
        
        # Create users
        user1 = await user_repo.create({
            "email": "user1@example.com",
            "username": "user1",
            "password_hash": "hash"
        })
        user2 = await user_repo.create({
            "email": "user2@example.com",
            "username": "user2",
            "password_hash": "hash"
        })
        
        # Create sync data for both users
        await sync_repo.create({
            "user_id": user1.id,
            "sync_type": "settings",
            "sync_key": "user_settings",
            "data": {"theme": "dark"},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        await sync_repo.create({
            "user_id": user2.id,
            "sync_type": "settings",
            "sync_key": "user_settings",
            "data": {"theme": "light"},
            "source_device_id": "device2",
            "source_device_type": "android"
        })
        
        # Get sync data for user1
        user1_sync = await sync_repo.get_sync_data_for_user(user1.id)
        
        assert len(user1_sync) == 1
        assert user1_sync[0].data == {"theme": "dark"}
    
    async def test_get_sync_data_by_type(self, test_session):
        """Test getting sync data by type."""
        user_repo = UserRepository(test_session)
        sync_repo = SyncRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create different types of sync data
        await sync_repo.create({
            "user_id": user.id,
            "sync_type": "commands",
            "sync_key": "cmd1",
            "data": {"commands": ["ls"]},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        await sync_repo.create({
            "user_id": user.id,
            "sync_type": "settings",
            "sync_key": "settings1",
            "data": {"theme": "dark"},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        
        # Get commands sync data
        commands_sync = await sync_repo.get_sync_data_by_type(
            user.id, "commands"
        )
        
        assert len(commands_sync) == 1
        assert commands_sync[0].sync_type == "commands"
        assert commands_sync[0].data == {"commands": ["ls"]}
    
    async def test_update_sync_data(self, test_session):
        """Test updating sync data."""
        user_repo = UserRepository(test_session)
        sync_repo = SyncRepository(test_session)
        
        # Create user and sync data
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        sync_data = await sync_repo.create({
            "user_id": user.id,
            "sync_type": "settings",
            "sync_key": "user_settings",
            "data": {"theme": "dark"},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        
        # Update sync data
        updated_sync = await sync_repo.update_sync_data(
            sync_data.id,
            new_data={"theme": "light"},
            device_id="device2",
            device_type="android"
        )
        
        assert updated_sync.data == {"theme": "light"}
        assert updated_sync.source_device_id == "device2"
        assert updated_sync.source_device_type == "android"
        assert updated_sync.version == 2  # Version incremented
    
    async def test_resolve_sync_conflict(self, test_session):
        """Test resolving sync conflicts."""
        user_repo = UserRepository(test_session)
        sync_repo = SyncRepository(test_session)
        
        # Create user and sync data
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        sync_data = await sync_repo.create({
            "user_id": user.id,
            "sync_type": "settings",
            "sync_key": "user_settings",
            "data": {"theme": "dark"},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        
        # Create conflict
        conflicting_data = {"theme": "light"}
        conflict_sync = await sync_repo.create_conflict(
            sync_data.id, conflicting_data
        )
        
        assert conflict_sync.has_conflict is True
        
        # Resolve conflict
        resolved_sync = await sync_repo.resolve_conflict(
            sync_data.id,
            chosen_data=conflicting_data,
            device_id="device2",
            device_type="web"
        )
        
        assert resolved_sync.has_conflict is False
        assert resolved_sync.data == conflicting_data
        assert resolved_sync.resolved_at is not None
    
    async def test_cleanup_old_sync_data(self, test_session):
        """Test cleaning up old sync data."""
        user_repo = UserRepository(test_session)
        sync_repo = SyncRepository(test_session)
        
        # Create user
        user = await user_repo.create({
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": "hash"
        })
        
        # Create old sync data
        old_sync = await sync_repo.create({
            "user_id": user.id,
            "sync_type": "commands",
            "sync_key": "old_commands",
            "data": {"commands": ["old"]},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        
        # Manually set old date
        old_date = datetime.utcnow() - timedelta(days=91)  # 91 days old
        old_sync.last_modified_at = old_date
        old_sync.created_at = old_date
        await test_session.commit()
        
        # Create recent sync data
        recent_sync = await sync_repo.create({
            "user_id": user.id,
            "sync_type": "commands",
            "sync_key": "recent_commands",
            "data": {"commands": ["recent"]},
            "source_device_id": "device1",
            "source_device_type": "ios"
        })
        
        # Cleanup old data (older than 90 days)
        cleaned_count = await sync_repo.cleanup_old_sync_data(days=90)
        
        assert cleaned_count == 1
        
        # Verify only recent data remains
        remaining_sync = await sync_repo.get_sync_data_for_user(user.id)
        assert len(remaining_sync) == 1
        assert remaining_sync[0].sync_key == "recent_commands"