"""
Test SSH management API endpoints.
"""

import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock

from tests.factories import (
    VerifiedUserFactory,
    SSHProfileFactory,
    SSHKeyFactory,
)


@pytest.mark.api
@pytest.mark.unit
class TestSSHProfileEndpoints:
    """Test SSH profile management endpoints."""

    async def test_create_ssh_profile_success(
        self, async_client, auth_headers, test_user
    ):
        """Test successful SSH profile creation."""
        profile_data = {
            "name": "Production Server",
            "description": "Main production server",
            "host": "prod.example.com",
            "port": 22,
            "username": "deploy",
            "auth_method": "key",
        }

        response = await async_client.post(
            "/api/ssh/profiles", json=profile_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["name"] == profile_data["name"]
        assert data["host"] == profile_data["host"]
        assert data["port"] == profile_data["port"]
        assert data["username"] == profile_data["username"]
        assert data["user_id"] == test_user.id
        assert "id" in data
        assert data["is_active"] is True

    async def test_create_ssh_profile_without_auth(self, async_client):
        """Test SSH profile creation without authentication."""
        profile_data = {
            "name": "Test Server",
            "host": "test.example.com",
            "username": "user",
        }

        response = await async_client.post("/api/ssh/profiles", json=profile_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_ssh_profile_invalid_data(self, async_client, auth_headers):
        """Test SSH profile creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name
            "host": "",  # Empty host
            "port": -1,  # Invalid port
            "username": "",  # Empty username
        }

        response = await async_client.post(
            "/api/ssh/profiles", json=invalid_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_ssh_profiles_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test getting user's SSH profiles."""
        # Create test profiles
        profile1 = SSHProfileFactory(user_id=test_user.id)
        profile2 = SSHProfileFactory(user_id=test_user.id)

        test_session.add_all([profile1, profile2])
        await test_session.commit()

        response = await async_client.get("/api/ssh/profiles", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 2
        profile_ids = {profile["id"] for profile in data}
        assert profile1.id in profile_ids
        assert profile2.id in profile_ids

    async def test_get_ssh_profiles_empty(self, async_client, auth_headers):
        """Test getting SSH profiles when user has none."""
        response = await async_client.get("/api/ssh/profiles", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data == []

    async def test_get_ssh_profile_by_id_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test getting specific SSH profile by ID."""
        profile = SSHProfileFactory(user_id=test_user.id)
        test_session.add(profile)
        await test_session.commit()

        response = await async_client.get(
            f"/api/ssh/profiles/{profile.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == profile.id
        assert data["name"] == profile.name
        assert data["host"] == profile.host

    async def test_get_ssh_profile_not_found(self, async_client, auth_headers):
        """Test getting non-existent SSH profile."""
        fake_id = "non-existent-id"

        response = await async_client.get(
            f"/api/ssh/profiles/{fake_id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_ssh_profile_unauthorized_access(
        self, async_client, auth_headers, test_session
    ):
        """Test accessing another user's SSH profile."""
        # Create profile for different user
        other_user = VerifiedUserFactory()
        profile = SSHProfileFactory(user_id=other_user.id)

        test_session.add_all([other_user, profile])
        await test_session.commit()

        response = await async_client.get(
            f"/api/ssh/profiles/{profile.id}", headers=auth_headers
        )

        assert (
            response.status_code == status.HTTP_404_NOT_FOUND
        )  # Should not reveal existence

    async def test_update_ssh_profile_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test successful SSH profile update."""
        profile = SSHProfileFactory(user_id=test_user.id)
        test_session.add(profile)
        await test_session.commit()

        update_data = {
            "name": "Updated Server Name",
            "description": "Updated description",
            "port": 2222,
        }

        response = await async_client.put(
            f"/api/ssh/profiles/{profile.id}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["port"] == update_data["port"]
        assert data["host"] == profile.host  # Unchanged

    async def test_delete_ssh_profile_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test successful SSH profile deletion."""
        profile = SSHProfileFactory(user_id=test_user.id)
        test_session.add(profile)
        await test_session.commit()

        response = await async_client.delete(
            f"/api/ssh/profiles/{profile.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify profile is deleted
        response = await async_client.get(
            f"/api/ssh/profiles/{profile.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("app.api.ssh.service.SSHClient")
    async def test_test_ssh_connection_success(
        self,
        mock_ssh_client,
        async_client,
        auth_headers,
        test_user,
        test_session,
    ):
        """Test successful SSH connection testing."""
        profile = SSHProfileFactory(user_id=test_user.id)
        test_session.add(profile)
        await test_session.commit()

        # Mock successful connection
        mock_client_instance = AsyncMock()
        mock_client_instance.connect.return_value = True
        mock_client_instance.test_connection.return_value = {
            "success": True,
            "message": "Connection successful",
            "latency_ms": 45,
        }
        mock_ssh_client.return_value = mock_client_instance

        response = await async_client.post(
            f"/api/ssh/profiles/{profile.id}/test", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "Connection successful" in data["message"]
        assert "latency_ms" in data

    @patch("app.api.ssh.service.SSHClient")
    async def test_test_ssh_connection_failure(
        self,
        mock_ssh_client,
        async_client,
        auth_headers,
        test_user,
        test_session,
    ):
        """Test SSH connection testing failure."""
        profile = SSHProfileFactory(user_id=test_user.id)
        test_session.add(profile)
        await test_session.commit()

        # Mock failed connection
        mock_client_instance = AsyncMock()
        mock_client_instance.connect.return_value = False
        mock_client_instance.test_connection.return_value = {
            "success": False,
            "message": "Connection failed: Authentication failed",
            "error": "Invalid credentials",
        }
        mock_ssh_client.return_value = mock_client_instance

        response = await async_client.post(
            f"/api/ssh/profiles/{profile.id}/test", headers=auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()

        assert data["success"] is False
        assert "Connection failed" in data["message"]


@pytest.mark.api
@pytest.mark.unit
class TestSSHKeyEndpoints:
    """Test SSH key management endpoints."""

    async def test_create_ssh_key_success(self, async_client, auth_headers, test_user):
        """Test successful SSH key creation."""
        key_data = {
            "name": "My Development Key",
            "description": "Key for development servers",
            "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC... user@example.com",
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAA...",
            "key_type": "rsa",
            "key_size": 4096,
            "has_passphrase": False,
        }

        response = await async_client.post(
            "/api/ssh/keys", json=key_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["name"] == key_data["name"]
        assert data["description"] == key_data["description"]
        assert data["key_type"] == key_data["key_type"]
        assert data["key_size"] == key_data["key_size"]
        assert data["user_id"] == test_user.id
        assert "id" in data
        assert "fingerprint" in data
        assert "private_key" not in data  # Should not return private key

    async def test_create_ssh_key_without_auth(self, async_client):
        """Test SSH key creation without authentication."""
        key_data = {
            "name": "Test Key",
            "public_key": "ssh-rsa AAAAB3...",
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----",
            "key_type": "rsa",
        }

        response = await async_client.post("/api/ssh/keys", json=key_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_ssh_keys_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test getting user's SSH keys."""
        # Create test keys
        key1 = SSHKeyFactory(user_id=test_user.id)
        key2 = SSHKeyFactory(user_id=test_user.id)

        test_session.add_all([key1, key2])
        await test_session.commit()

        response = await async_client.get("/api/ssh/keys", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) == 2
        key_ids = {key["id"] for key in data}
        assert key1.id in key_ids
        assert key2.id in key_ids

        # Verify sensitive data is not returned
        for key in data:
            assert "encrypted_private_key" not in key
            assert "private_key" not in key

    async def test_get_ssh_key_by_id_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test getting specific SSH key by ID."""
        key = SSHKeyFactory(user_id=test_user.id)
        test_session.add(key)
        await test_session.commit()

        response = await async_client.get(
            f"/api/ssh/keys/{key.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == key.id
        assert data["name"] == key.name
        assert data["key_type"] == key.key_type
        assert "fingerprint" in data
        assert "encrypted_private_key" not in data

    async def test_update_ssh_key_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test successful SSH key update."""
        key = SSHKeyFactory(user_id=test_user.id)
        test_session.add(key)
        await test_session.commit()

        update_data = {
            "name": "Updated Key Name",
            "description": "Updated description",
        }

        response = await async_client.put(
            f"/api/ssh/keys/{key.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["key_type"] == key.key_type  # Unchanged

    async def test_delete_ssh_key_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test successful SSH key deletion."""
        key = SSHKeyFactory(user_id=test_user.id)
        test_session.add(key)
        await test_session.commit()

        response = await async_client.delete(
            f"/api/ssh/keys/{key.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify key is deleted
        response = await async_client.get(
            f"/api/ssh/keys/{key.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_ssh_key_usage_tracking(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test SSH key usage tracking."""
        key = SSHKeyFactory(user_id=test_user.id, usage_count=5)
        test_session.add(key)
        await test_session.commit()

        # Record key usage
        response = await async_client.post(
            f"/api/ssh/keys/{key.id}/use", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify usage count increased
        response = await async_client.get(
            f"/api/ssh/keys/{key.id}", headers=auth_headers
        )
        data = response.json()

        assert data["usage_count"] == 6
        assert "last_used_at" in data


@pytest.mark.api
@pytest.mark.unit
class TestSSHProfileKeyAssociation:
    """Test SSH profile and key association endpoints."""

    async def test_assign_key_to_profile_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test successfully assigning SSH key to profile."""
        profile = SSHProfileFactory(user_id=test_user.id, ssh_key_id=None)
        key = SSHKeyFactory(user_id=test_user.id)

        test_session.add_all([profile, key])
        await test_session.commit()

        assignment_data = {"ssh_key_id": key.id}

        response = await async_client.put(
            f"/api/ssh/profiles/{profile.id}/key",
            json=assignment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["ssh_key_id"] == key.id
        assert "ssh_key" in data
        assert data["ssh_key"]["name"] == key.name

    async def test_assign_nonexistent_key_to_profile(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test assigning non-existent SSH key to profile."""
        profile = SSHProfileFactory(user_id=test_user.id)
        test_session.add(profile)
        await test_session.commit()

        assignment_data = {"ssh_key_id": "non-existent-key-id"}

        response = await async_client.put(
            f"/api/ssh/profiles/{profile.id}/key",
            json=assignment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_assign_other_users_key_to_profile(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test assigning another user's SSH key to profile."""
        profile = SSHProfileFactory(user_id=test_user.id)

        # Create key for different user
        other_user = VerifiedUserFactory()
        other_key = SSHKeyFactory(user_id=other_user.id)

        test_session.add_all([profile, other_user, other_key])
        await test_session.commit()

        assignment_data = {"ssh_key_id": other_key.id}

        response = await async_client.put(
            f"/api/ssh/profiles/{profile.id}/key",
            json=assignment_data,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_remove_key_from_profile_success(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test successfully removing SSH key from profile."""
        key = SSHKeyFactory(user_id=test_user.id)
        profile = SSHProfileFactory(user_id=test_user.id, ssh_key_id=key.id)

        test_session.add_all([key, profile])
        await test_session.commit()

        response = await async_client.delete(
            f"/api/ssh/profiles/{profile.id}/key", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["ssh_key_id"] is None
        assert "ssh_key" not in data or data["ssh_key"] is None


@pytest.mark.api
@pytest.mark.unit
class TestSSHConfigGeneration:
    """Test SSH config generation endpoints."""

    async def test_generate_ssh_config_single_profile(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test generating SSH config for single profile."""
        key = SSHKeyFactory(user_id=test_user.id, file_path="/home/user/.ssh/id_rsa")
        profile = SSHProfileFactory(
            user_id=test_user.id,
            ssh_key_id=key.id,
            name="prodserver",
            host="prod.example.com",
            port=22,
            username="deploy",
        )

        test_session.add_all([key, profile])
        await test_session.commit()

        response = await async_client.get(
            f"/api/ssh/profiles/{profile.id}/config", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "config" in data
        config = data["config"]

        assert "Host prodserver" in config
        assert "HostName prod.example.com" in config
        assert "Port 22" in config
        assert "User deploy" in config
        assert "IdentityFile /home/user/.ssh/id_rsa" in config

    async def test_generate_ssh_config_all_profiles(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test generating SSH config for all user profiles."""
        # Create multiple profiles
        key1 = SSHKeyFactory(user_id=test_user.id)
        key2 = SSHKeyFactory(user_id=test_user.id)

        profile1 = SSHProfileFactory(
            user_id=test_user.id, ssh_key_id=key1.id, name="server1"
        )
        profile2 = SSHProfileFactory(
            user_id=test_user.id, ssh_key_id=key2.id, name="server2"
        )

        test_session.add_all([key1, key2, profile1, profile2])
        await test_session.commit()

        response = await async_client.get("/api/ssh/config", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "config" in data
        config = data["config"]

        assert "Host server1" in config
        assert "Host server2" in config
        assert config.count("Host ") == 2  # Should have two host entries


@pytest.mark.api
@pytest.mark.unit
class TestSSHStatistics:
    """Test SSH statistics and analytics endpoints."""

    async def test_get_ssh_profile_statistics(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test getting SSH profile statistics."""
        # Create profiles with different usage patterns
        profile1 = SSHProfileFactory(
            user_id=test_user.id,
            connection_count=50,
            successful_connections=45,
            failed_connections=5,
        )
        profile2 = SSHProfileFactory(
            user_id=test_user.id,
            connection_count=20,
            successful_connections=18,
            failed_connections=2,
        )

        test_session.add_all([profile1, profile2])
        await test_session.commit()

        response = await async_client.get(
            "/api/ssh/profiles/statistics", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_profiles" in data
        assert "total_connections" in data
        assert "success_rate" in data
        assert "most_used_profile" in data

        assert data["total_profiles"] == 2
        assert data["total_connections"] == 70
        assert data["success_rate"] > 0  # Should be positive percentage

    async def test_get_ssh_key_statistics(
        self, async_client, auth_headers, test_user, test_session
    ):
        """Test getting SSH key statistics."""
        # Create keys with different usage patterns
        key1 = SSHKeyFactory(user_id=test_user.id, usage_count=100, key_type="rsa")
        key2 = SSHKeyFactory(user_id=test_user.id, usage_count=50, key_type="ed25519")
        key3 = SSHKeyFactory(user_id=test_user.id, usage_count=25, key_type="ecdsa")

        test_session.add_all([key1, key2, key3])
        await test_session.commit()

        response = await async_client.get(
            "/api/ssh/keys/statistics", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_keys" in data
        assert "total_usage" in data
        assert "key_types" in data
        assert "most_used_key" in data

        assert data["total_keys"] == 3
        assert data["total_usage"] == 175
        assert "rsa" in data["key_types"]
        assert "ed25519" in data["key_types"]
        assert "ecdsa" in data["key_types"]
