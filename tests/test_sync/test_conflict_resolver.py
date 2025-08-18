"""
Comprehensive tests for ConflictResolver to achieve 70% coverage.

Tests all conflict resolution strategies and scenarios:
- Last write wins strategy
- Merge strategy (commands, SSH profiles, settings, simple data)
- User choice strategy
- Local/remote wins strategies
- Conflict detection algorithms
- SSH profile merging
- Timestamp extraction with various formats
- Error handling and edge cases
- Automatic conflict resolution
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

from app.api.sync.services.conflict_resolver import ConflictResolver


@pytest.mark.asyncio
class TestConflictResolver:
    """Comprehensive tests for ConflictResolver functionality."""

    @pytest.fixture
    def resolver(self):
        """Create ConflictResolver instance for testing."""
        return ConflictResolver()

    @pytest.fixture
    def sample_local_data(self):
        """Sample local data for testing."""
        return {
            "id": "local-123",
            "name": "Local Item",
            "value": 100,
            "timestamp": "2023-01-01T10:00:00+00:00",
            "version": 1,
            "commands": ["ls", "pwd"],
            "ssh_profiles": [
                {
                    "name": "server1",
                    "host": "local.example.com",
                    "timestamp": "2023-01-01T09:00:00+00:00"
                }
            ],
            "settings": {
                "theme": "dark",
                "notifications": True
            }
        }

    @pytest.fixture
    def sample_remote_data(self):
        """Sample remote data for testing."""
        return {
            "id": "remote-123",
            "name": "Remote Item",
            "value": 200,
            "timestamp": "2023-01-01T11:00:00+00:00",
            "version": 2,
            "commands": ["pwd", "whoami"],
            "ssh_profiles": [
                {
                    "name": "server1",
                    "host": "remote.example.com",
                    "timestamp": "2023-01-01T10:30:00+00:00"
                }
            ],
            "settings": {
                "theme": "light",
                "auto_save": True
            }
        }

    # Test Basic Resolution Strategies
    async def test_resolve_last_write_wins_remote_newer(self, resolver, sample_local_data, sample_remote_data):
        """Test last write wins when remote is newer."""
        result = await resolver.resolve(sample_local_data, sample_remote_data, "last_write_wins")
        
        assert result == sample_remote_data
        assert result["name"] == "Remote Item"

    async def test_resolve_last_write_wins_local_newer(self, resolver, sample_local_data, sample_remote_data):
        """Test last write wins when local is newer."""
        # Make local data newer
        sample_local_data["timestamp"] = "2023-01-01T12:00:00+00:00"
        
        result = await resolver.resolve(sample_local_data, sample_remote_data, "last_write_wins")
        
        assert result == sample_local_data
        assert result["name"] == "Local Item"

    async def test_resolve_local_wins_strategy(self, resolver, sample_local_data, sample_remote_data):
        """Test local wins strategy."""
        result = await resolver.resolve(sample_local_data, sample_remote_data, "local_wins")
        
        assert result == sample_local_data
        assert result["name"] == "Local Item"

    async def test_resolve_remote_wins_strategy(self, resolver, sample_local_data, sample_remote_data):
        """Test remote wins strategy."""
        result = await resolver.resolve(sample_local_data, sample_remote_data, "remote_wins")
        
        assert result == sample_remote_data
        assert result["name"] == "Remote Item"

    async def test_resolve_user_choice_local(self, resolver, sample_local_data, sample_remote_data):
        """Test user choice strategy selecting local."""
        result = await resolver.resolve(
            sample_local_data, sample_remote_data, "user_choice", user_preference="local"
        )
        
        assert result == sample_local_data
        assert result["name"] == "Local Item"

    async def test_resolve_user_choice_remote(self, resolver, sample_local_data, sample_remote_data):
        """Test user choice strategy selecting remote."""
        result = await resolver.resolve(
            sample_local_data, sample_remote_data, "user_choice", user_preference="remote"
        )
        
        assert result == sample_remote_data
        assert result["name"] == "Remote Item"

    async def test_resolve_user_choice_no_preference(self, resolver, sample_local_data, sample_remote_data):
        """Test user choice strategy with no preference defaults to local."""
        with patch('app.core.logging.logger.warning') as mock_warning:
            result = await resolver.resolve(
                sample_local_data, sample_remote_data, "user_choice", user_preference=None
            )
            
            assert result == sample_local_data
            mock_warning.assert_called_once()

    async def test_resolve_user_choice_invalid_preference(self, resolver, sample_local_data, sample_remote_data):
        """Test user choice strategy with invalid preference defaults to local."""
        with patch('app.core.logging.logger.warning') as mock_warning:
            result = await resolver.resolve(
                sample_local_data, sample_remote_data, "user_choice", user_preference="invalid"
            )
            
            assert result == sample_local_data
            mock_warning.assert_called_once()

    async def test_resolve_unsupported_strategy(self, resolver, sample_local_data, sample_remote_data):
        """Test resolve with unsupported strategy falls back to last_write_wins."""
        with patch('app.core.logging.logger.warning') as mock_warning:
            result = await resolver.resolve(
                sample_local_data, sample_remote_data, "unsupported_strategy"
            )
            
            assert result == sample_remote_data  # Remote is newer in fixture
            mock_warning.assert_called_once()

    # Test Merge Strategy
    async def test_resolve_merge_command_lists(self, resolver):
        """Test merge strategy with command lists."""
        local_data = {
            "commands": ["ls", "pwd", "cd"],
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        remote_data = {
            "commands": ["pwd", "whoami", "ps"],
            "timestamp": "2023-01-01T11:00:00+00:00"
        }
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        merged_commands = set(result["commands"])
        expected_commands = {"ls", "pwd", "cd", "whoami", "ps"}
        assert merged_commands == expected_commands
        assert "merge_timestamp" in result

    async def test_resolve_merge_ssh_profiles(self, resolver):
        """Test merge strategy with SSH profiles."""
        local_data = {
            "ssh_profiles": [
                {"name": "server1", "host": "local1.com", "timestamp": "2023-01-01T09:00:00+00:00"},
                {"name": "server2", "host": "local2.com", "timestamp": "2023-01-01T09:00:00+00:00"}
            ]
        }
        remote_data = {
            "ssh_profiles": [
                {"name": "server1", "host": "remote1.com", "timestamp": "2023-01-01T10:00:00+00:00"},
                {"name": "server3", "host": "remote3.com", "timestamp": "2023-01-01T10:00:00+00:00"}
            ]
        }
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        profiles = {p["name"]: p for p in result["ssh_profiles"]}
        assert len(profiles) == 3
        assert profiles["server1"]["host"] == "remote1.com"  # Remote is newer
        assert profiles["server2"]["host"] == "local2.com"   # Only in local
        assert profiles["server3"]["host"] == "remote3.com"  # Only in remote

    async def test_resolve_merge_settings(self, resolver):
        """Test merge strategy with settings dictionary."""
        local_data = {
            "settings": {
                "theme": "dark",
                "notifications": True,
                "auto_save": False
            }
        }
        remote_data = {
            "settings": {
                "theme": "light",
                "font_size": 14,
                "auto_save": True
            }
        }
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        settings = result["settings"]
        assert settings["theme"] == "light"           # Remote overwrites
        assert settings["notifications"] is True      # Local only
        assert settings["font_size"] == 14           # Remote only
        assert settings["auto_save"] is True         # Remote overwrites

    async def test_resolve_merge_simple_data(self, resolver):
        """Test merge strategy with simple data fields."""
        local_data = {
            "name": "Local",
            "value": 100,
            "category": "local_only",
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        remote_data = {
            "name": "Remote",
            "status": "active",
            "timestamp": "2023-01-01T11:00:00+00:00"
        }
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        assert result["name"] == "Remote"           # Remote overwrites
        assert result["value"] == 100              # Local only
        assert result["category"] == "local_only"  # Local only
        assert result["status"] == "active"        # Remote only
        assert "merge_timestamp" in result

    # Test SSH Profile Merging
    async def test_merge_ssh_profiles_success(self, resolver):
        """Test SSH profile merging with various scenarios."""
        local_profiles = [
            {"name": "server1", "host": "local1.com", "timestamp": "2023-01-01T10:00:00+00:00"},
            {"name": "server2", "host": "local2.com", "timestamp": "2023-01-01T09:00:00+00:00"}
        ]
        remote_profiles = [
            {"name": "server1", "host": "remote1.com", "timestamp": "2023-01-01T11:00:00+00:00"},
            {"name": "server3", "host": "remote3.com", "timestamp": "2023-01-01T10:00:00+00:00"}
        ]
        
        result = await resolver._merge_ssh_profiles(local_profiles, remote_profiles)
        
        profiles_by_name = {p["name"]: p for p in result}
        assert len(profiles_by_name) == 3
        assert profiles_by_name["server1"]["host"] == "remote1.com"  # Remote newer
        assert profiles_by_name["server2"]["host"] == "local2.com"   # Local only
        assert profiles_by_name["server3"]["host"] == "remote3.com"  # Remote only

    async def test_merge_ssh_profiles_no_name(self, resolver):
        """Test SSH profile merging ignores profiles without names."""
        local_profiles = [
            {"host": "local1.com", "timestamp": "2023-01-01T10:00:00+00:00"},  # No name
            {"name": "server2", "host": "local2.com", "timestamp": "2023-01-01T09:00:00+00:00"}
        ]
        remote_profiles = [
            {"name": "", "host": "remote1.com", "timestamp": "2023-01-01T11:00:00+00:00"},  # Empty name
            {"name": "server3", "host": "remote3.com", "timestamp": "2023-01-01T10:00:00+00:00"}
        ]
        
        result = await resolver._merge_ssh_profiles(local_profiles, remote_profiles)
        
        profiles_by_name = {p["name"]: p for p in result if p.get("name")}
        assert len(profiles_by_name) == 2
        assert "server2" in profiles_by_name
        assert "server3" in profiles_by_name

    async def test_merge_ssh_profiles_local_newer(self, resolver):
        """Test SSH profile merging when local profile is newer."""
        local_profiles = [
            {"name": "server1", "host": "local1.com", "timestamp": "2023-01-01T12:00:00+00:00"}
        ]
        remote_profiles = [
            {"name": "server1", "host": "remote1.com", "timestamp": "2023-01-01T11:00:00+00:00"}
        ]
        
        result = await resolver._merge_ssh_profiles(local_profiles, remote_profiles)
        
        assert len(result) == 1
        assert result[0]["host"] == "local1.com"  # Local is newer

    # Test Timestamp Extraction
    def test_extract_timestamp_various_fields(self, resolver):
        """Test timestamp extraction from various field names."""
        test_cases = [
            ({"timestamp": "2023-01-01T10:00:00+00:00"}, "timestamp"),
            ({"modified_at": "2023-01-01T10:00:00+00:00"}, "modified_at"),
            ({"updated_at": "2023-01-01T10:00:00+00:00"}, "updated_at"),
            ({"last_modified_at": "2023-01-01T10:00:00+00:00"}, "last_modified_at"),
            ({"created_at": "2023-01-01T10:00:00+00:00"}, "created_at"),
        ]
        
        for data, field_name in test_cases:
            result = resolver._extract_timestamp(data)
            assert result.year == 2023
            assert result.month == 1
            assert result.day == 1

    def test_extract_timestamp_z_format(self, resolver):
        """Test timestamp extraction with Z timezone format."""
        data = {"timestamp": "2023-01-01T10:00:00Z"}
        result = resolver._extract_timestamp(data)
        
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1

    def test_extract_timestamp_no_timezone(self, resolver):
        """Test timestamp extraction without timezone."""
        data = {"timestamp": "2023-01-01T10:00:00"}
        result = resolver._extract_timestamp(data)
        
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1

    def test_extract_timestamp_invalid_format(self, resolver):
        """Test timestamp extraction with invalid format falls back to datetime.min."""
        data = {"timestamp": "invalid-date-format"}
        result = resolver._extract_timestamp(data)
        
        assert result == datetime.min

    def test_extract_timestamp_non_string(self, resolver):
        """Test timestamp extraction with non-string value."""
        data = {"timestamp": 1234567890}
        result = resolver._extract_timestamp(data)
        
        assert result == datetime.min

    def test_extract_timestamp_no_timestamp_fields(self, resolver):
        """Test timestamp extraction with no timestamp fields."""
        data = {"name": "test", "value": 123}
        result = resolver._extract_timestamp(data)
        
        assert result == datetime.min

    def test_extract_timestamp_empty_timestamp(self, resolver):
        """Test timestamp extraction with empty timestamp."""
        data = {"timestamp": "", "modified_at": None}
        result = resolver._extract_timestamp(data)
        
        assert result == datetime.min

    # Test Conflict Detection
    async def test_detect_conflicts_version_mismatch(self, resolver):
        """Test conflict detection with version mismatch."""
        local_data = {"version": 1, "name": "test"}
        remote_data = {"version": 2, "name": "test"}
        
        conflicts = await resolver.detect_conflicts(local_data, remote_data)
        
        assert conflicts["has_conflicts"] is True
        assert conflicts["conflict_type"] == "version_mismatch"
        assert "version" in conflicts["conflicting_fields"]

    async def test_detect_conflicts_data_differences(self, resolver):
        """Test conflict detection with data differences."""
        local_data = {
            "name": "local",
            "value": 100,
            "category": "test",
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        remote_data = {
            "name": "remote",
            "value": 100,
            "status": "active",
            "timestamp": "2023-01-01T11:00:00+00:00"
        }
        
        conflicts = await resolver.detect_conflicts(local_data, remote_data)
        
        assert conflicts["has_conflicts"] is True
        assert "name" in conflicts["conflicting_fields"]
        assert "status" in conflicts["conflicting_fields"]
        assert "value" not in conflicts["conflicting_fields"]  # Same value
        assert "timestamp" not in conflicts["conflicting_fields"]  # Metadata field

    async def test_detect_conflicts_no_conflicts(self, resolver):
        """Test conflict detection with no conflicts."""
        data = {"name": "test", "value": 100}
        
        conflicts = await resolver.detect_conflicts(data, data)
        
        assert conflicts["has_conflicts"] is False
        assert len(conflicts["conflicting_fields"]) == 0

    async def test_detect_conflicts_resolution_suggestions(self, resolver):
        """Test conflict detection resolution suggestions."""
        local_data = {
            "name": "local",
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        remote_data = {
            "name": "remote",
            "timestamp": "2023-01-01T11:00:00+00:00"
        }
        
        conflicts = await resolver.detect_conflicts(local_data, remote_data)
        
        assert "remote_wins" in conflicts["resolution_suggestions"]

    async def test_detect_conflicts_equal_timestamps(self, resolver):
        """Test conflict detection with equal timestamps suggests user choice."""
        local_data = {
            "name": "local",
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        remote_data = {
            "name": "remote",
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        
        conflicts = await resolver.detect_conflicts(local_data, remote_data)
        
        assert "user_choice" in conflicts["resolution_suggestions"]

    async def test_detect_conflicts_multiple_fields_suggests_merge(self, resolver):
        """Test conflict detection suggests merge for multiple conflicting fields."""
        local_data = {
            "name": "local",
            "value": 100,
            "category": "test",
            "timestamp": "2023-01-01T10:00:00+00:00"
        }
        remote_data = {
            "name": "remote",
            "value": 200,
            "status": "active",
            "timestamp": "2023-01-01T11:00:00+00:00"
        }
        
        conflicts = await resolver.detect_conflicts(local_data, remote_data)
        
        assert "merge" in conflicts["resolution_suggestions"]

    # Test Conflict Report Creation
    async def test_create_conflict_report_success(self, resolver, sample_local_data, sample_remote_data):
        """Test successful conflict report creation."""
        sync_key = "test_sync_key"
        
        with patch.object(resolver, 'detect_conflicts') as mock_detect:
            mock_conflicts = {
                "has_conflicts": True,
                "conflict_type": "data_mismatch",
                "conflicting_fields": ["name", "value"],
                "resolution_suggestions": ["merge", "remote_wins"]
            }
            mock_detect.return_value = mock_conflicts
            
            report = await resolver.create_conflict_report(
                sample_local_data, sample_remote_data, sync_key
            )
            
            assert report["sync_key"] == sync_key
            assert "conflict_id" in report
            assert "detected_at" in report
            assert report["local_data"] == sample_local_data
            assert report["remote_data"] == sample_remote_data
            assert report["conflicts"] == mock_conflicts
            assert report["recommended_strategy"] == "merge"

    async def test_create_conflict_report_no_suggestions(self, resolver, sample_local_data, sample_remote_data):
        """Test conflict report creation with no resolution suggestions."""
        with patch.object(resolver, 'detect_conflicts') as mock_detect:
            mock_conflicts = {
                "has_conflicts": True,
                "resolution_suggestions": []
            }
            mock_detect.return_value = mock_conflicts
            
            report = await resolver.create_conflict_report(
                sample_local_data, sample_remote_data, "test_key"
            )
            
            assert report["recommended_strategy"] == "last_write_wins"

    # Test Automatic Conflict Resolution
    async def test_resolve_conflict_automatically_success(self, resolver):
        """Test successful automatic conflict resolution."""
        conflict_report = {
            "conflict_id": "test_conflict_123",
            "local_data": {"name": "local", "timestamp": "2023-01-01T10:00:00+00:00"},
            "remote_data": {"name": "remote", "timestamp": "2023-01-01T11:00:00+00:00"},
            "recommended_strategy": "last_write_wins"
        }
        
        result = await resolver.resolve_conflict_automatically(conflict_report)
        
        assert result["success"] is True
        assert result["conflict_id"] == "test_conflict_123"
        assert result["strategy_used"] == "last_write_wins"
        assert result["resolved_data"]["name"] == "remote"  # Remote is newer
        assert "resolved_at" in result

    async def test_resolve_conflict_automatically_no_strategy(self, resolver):
        """Test automatic conflict resolution with no strategy defaults to last_write_wins."""
        conflict_report = {
            "conflict_id": "test_conflict_123",
            "local_data": {"name": "local", "timestamp": "2023-01-01T10:00:00+00:00"},
            "remote_data": {"name": "remote", "timestamp": "2023-01-01T11:00:00+00:00"}
        }
        
        result = await resolver.resolve_conflict_automatically(conflict_report)
        
        assert result["success"] is True
        assert result["strategy_used"] == "last_write_wins"

    # Test Error Handling
    async def test_resolve_exception_handling(self, resolver, sample_local_data, sample_remote_data):
        """Test resolve method exception handling."""
        with patch.object(resolver, '_resolve_last_write_wins', side_effect=Exception("Test error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver.resolve(sample_local_data, sample_remote_data, "last_write_wins")
                
                assert result == sample_local_data  # Fallback to local
                mock_error.assert_called_once()

    async def test_last_write_wins_exception_handling(self, resolver, sample_local_data, sample_remote_data):
        """Test last write wins exception handling."""
        with patch.object(resolver, '_extract_timestamp', side_effect=Exception("Timestamp error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver._resolve_last_write_wins(sample_local_data, sample_remote_data)
                
                assert result == sample_local_data  # Fallback to local
                mock_error.assert_called_once()

    async def test_merge_exception_handling(self, resolver, sample_local_data, sample_remote_data):
        """Test merge strategy exception handling."""
        with patch('copy.copy', side_effect=Exception("Copy error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver._resolve_merge(sample_local_data, sample_remote_data)
                
                assert result == sample_local_data  # Fallback to local
                mock_error.assert_called_once()

    async def test_user_choice_exception_handling(self, resolver, sample_local_data, sample_remote_data):
        """Test user choice strategy exception handling."""
        # Simulate exception by making the data access fail
        with patch('app.core.logging.logger.error') as mock_error:
            # Force an exception in the user choice logic
            with patch.object(resolver, '_resolve_user_choice', side_effect=Exception("User choice error")):
                # This will call the original resolve method which will catch the exception
                result = await resolver.resolve(
                    sample_local_data, sample_remote_data, "user_choice", user_preference="local"
                )
                
                assert result == sample_local_data  # Fallback to local
                mock_error.assert_called_once()

    async def test_merge_ssh_profiles_exception_handling(self, resolver):
        """Test SSH profile merging exception handling."""
        local_profiles = [{"name": "server1"}]
        remote_profiles = [{"name": "server2"}]
        
        with patch.object(resolver, '_extract_timestamp', side_effect=Exception("Timestamp error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver._merge_ssh_profiles(local_profiles, remote_profiles)
                
                assert result == local_profiles  # Fallback to local
                mock_error.assert_called_once()

    def test_extract_timestamp_exception_handling(self, resolver):
        """Test timestamp extraction exception handling."""
        # Create data that will cause an exception
        data = {"timestamp": "2023-01-01T10:00:00+00:00"}
        
        with patch('datetime.datetime.fromisoformat', side_effect=Exception("Parse error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = resolver._extract_timestamp(data)
                
                assert result == datetime.min
                mock_error.assert_called_once()

    async def test_detect_conflicts_exception_handling(self, resolver, sample_local_data, sample_remote_data):
        """Test conflict detection exception handling."""
        with patch.object(resolver, '_extract_timestamp', side_effect=Exception("Timestamp error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver.detect_conflicts(sample_local_data, sample_remote_data)
                
                assert result["has_conflicts"] is False
                assert "error" in result
                mock_error.assert_called_once()

    async def test_create_conflict_report_exception_handling(self, resolver, sample_local_data, sample_remote_data):
        """Test conflict report creation exception handling."""
        with patch.object(resolver, 'detect_conflicts', side_effect=Exception("Detection error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver.create_conflict_report(
                    sample_local_data, sample_remote_data, "test_key"
                )
                
                assert "error" in result
                mock_error.assert_called_once()

    async def test_resolve_conflict_automatically_exception_handling(self, resolver):
        """Test automatic conflict resolution exception handling."""
        conflict_report = {
            "local_data": {"name": "local"},
            "remote_data": {"name": "remote"}
        }
        
        with patch.object(resolver, 'resolve', side_effect=Exception("Resolution error")):
            with patch('app.core.logging.logger.error') as mock_error:
                result = await resolver.resolve_conflict_automatically(conflict_report)
                
                assert result["success"] is False
                assert "error" in result
                mock_error.assert_called_once()

    # Test Supported Strategies
    def test_supported_strategies(self, resolver):
        """Test that all expected strategies are supported."""
        expected_strategies = {
            "last_write_wins",
            "merge",
            "user_choice", 
            "local_wins",
            "remote_wins"
        }
        
        assert resolver.supported_strategies == expected_strategies

    # Test Edge Cases
    async def test_resolve_with_empty_data(self, resolver):
        """Test resolve with empty data."""
        local_data = {}
        remote_data = {}
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "merge_timestamp" in result

    async def test_resolve_with_none_values(self, resolver):
        """Test resolve with None values in data."""
        local_data = {"name": None, "value": 100}
        remote_data = {"name": "test", "value": None}
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        assert result["name"] == "test"  # Remote overwrites None
        assert result["value"] == 100    # Local value preserved

    async def test_merge_with_nested_data(self, resolver):
        """Test merge with nested data structures."""
        local_data = {
            "config": {
                "database": {"host": "localhost", "port": 5432},
                "cache": {"enabled": True}
            }
        }
        remote_data = {
            "config": {
                "database": {"host": "remote.db", "timeout": 30},
                "logging": {"level": "INFO"}
            }
        }
        
        result = await resolver.resolve(local_data, remote_data, "merge")
        
        # Simple merge should overwrite the entire config
        assert result["config"] == remote_data["config"]

    async def test_conflict_detection_with_complex_data(self, resolver):
        """Test conflict detection with complex nested data."""
        local_data = {
            "settings": {"theme": "dark"},
            "metadata": {"version": 1}
        }
        remote_data = {
            "settings": {"theme": "light"},
            "metadata": {"version": 1}
        }
        
        conflicts = await resolver.detect_conflicts(local_data, remote_data)
        
        assert conflicts["has_conflicts"] is True
        assert "settings" in conflicts["conflicting_fields"]
        assert "metadata" not in conflicts["conflicting_fields"]  # Same value