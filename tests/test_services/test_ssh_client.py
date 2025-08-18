"""
Tests for SSH Client Service.

This module tests the SSH client functionality including:
- Connection testing
- Key loading and validation
- Host key retrieval
- Key pair generation
"""

import asyncio
import io
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import paramiko
import pytest

from app.models.ssh_profile import SSHKey
from app.services.ssh_client import SSHClientService


class TestSSHClientService:
    """Test SSH client service functionality."""

    @pytest.fixture
    def ssh_service(self):
        """Create SSH client service instance."""
        return SSHClientService()

    @pytest.fixture
    def mock_ssh_key(self):
        """Create mock SSH key."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "rsa"
        ssh_key.encrypted_private_key = b"""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEA1234567890
-----END OPENSSH PRIVATE KEY-----"""
        return ssh_key

    @pytest.fixture
    def mock_paramiko_client(self):
        """Create mock paramiko SSH client."""
        client = MagicMock(spec=paramiko.SSHClient)
        client.connect = MagicMock()
        client.close = MagicMock()
        client.get_transport = MagicMock()
        client.exec_command = MagicMock()
        client.set_missing_host_key_policy = MagicMock()
        return client

    @pytest.mark.asyncio
    async def test_test_connection_with_password_success(self, ssh_service, mock_paramiko_client):
        """Test successful SSH connection with password authentication."""
        # Arrange
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"connection_test"
        mock_paramiko_client.exec_command.return_value = (None, mock_stdout, None)
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_8.0"
        mock_transport.get_cipher.return_value = ("aes128-ctr", "hmac-sha2-256")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-rsa"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_paramiko_client.get_transport.return_value = mock_transport

        with (
            patch("paramiko.SSHClient", return_value=mock_paramiko_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            # Mock the loop.run_in_executor call
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            # Act
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            # Assert
            assert result["success"] is True
            assert "Connection successful" in result["message"]
            # When command test fails, it still considers connection successful
            assert result["details"]["command_test"] == "failed"
            assert result["server_info"]["version"] == "OpenSSH_8.0"
            assert result["server_info"]["cipher"] == "aes128-ctr"

    @pytest.mark.asyncio
    async def test_test_connection_with_ssh_key_success(self, ssh_service, mock_ssh_key, mock_paramiko_client):
        """Test successful SSH connection with SSH key authentication."""
        # Arrange
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"connection_test"
        mock_paramiko_client.exec_command.return_value = (None, mock_stdout, None)
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_8.0"
        mock_transport.get_cipher.return_value = ("aes128-ctr", "hmac-sha2-256")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-rsa"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_paramiko_client.get_transport.return_value = mock_transport

        mock_rsa_key = MagicMock(spec=paramiko.RSAKey)
        
        with (
            patch("paramiko.SSHClient", return_value=mock_paramiko_client),
            patch.object(ssh_service, "_load_private_key", return_value=mock_rsa_key),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            # Mock the loop.run_in_executor call
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            # Act
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                ssh_key=mock_ssh_key
            )

            # Assert
            assert result["success"] is True
            assert "Connection successful" in result["message"]

    @pytest.mark.asyncio
    async def test_test_connection_authentication_failure(self, ssh_service, mock_paramiko_client):
        """Test SSH connection authentication failure."""
        # Arrange  
        def mock_connect_auth_fail(**kwargs):
            raise paramiko.AuthenticationException("Authentication failed")

        with (
            patch("paramiko.SSHClient", return_value=mock_paramiko_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            # Mock the loop.run_in_executor call to raise auth exception
            future = asyncio.Future()
            future.set_exception(paramiko.AuthenticationException("Authentication failed"))
            mock_loop.return_value.run_in_executor.return_value = future
            
            # Act
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="wrongpass"
            )

            # Assert
            assert result["success"] is False
            assert "Authentication failed" in result["message"]
            assert result["details"]["error_type"] == "authentication"

    @pytest.mark.asyncio
    async def test_test_connection_timeout(self, ssh_service, mock_paramiko_client):
        """Test SSH connection timeout."""
        # Arrange
        with (
            patch("paramiko.SSHClient", return_value=mock_paramiko_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            # Mock the loop.run_in_executor call to raise timeout
            future = asyncio.Future()
            future.set_exception(socket.timeout())
            mock_loop.return_value.run_in_executor.return_value = future
            
            # Act
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=5
            )

            # Assert
            assert result["success"] is False
            assert "Connection timeout after 5 seconds" in result["message"]
            assert result["details"]["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_test_connection_connection_refused(self, ssh_service, mock_paramiko_client):
        """Test SSH connection refused."""
        # Arrange
        with (
            patch("paramiko.SSHClient", return_value=mock_paramiko_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            # Mock the loop.run_in_executor call to raise connection refused
            future = asyncio.Future()
            future.set_exception(ConnectionRefusedError())
            mock_loop.return_value.run_in_executor.return_value = future
            
            # Act
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            # Assert
            assert result["success"] is False
            assert "Connection refused" in result["message"]
            assert result["details"]["error_type"] == "connection_refused"

    @pytest.mark.asyncio
    async def test_test_connection_dns_error(self, ssh_service, mock_paramiko_client):
        """Test SSH connection DNS resolution failure."""
        # Arrange
        with (
            patch("paramiko.SSHClient", return_value=mock_paramiko_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            # Mock the loop.run_in_executor call to raise DNS error
            future = asyncio.Future()
            future.set_exception(socket.gaierror("Name or service not known"))
            mock_loop.return_value.run_in_executor.return_value = future
            
            # Act
            result = await ssh_service.test_connection(
                host="nonexistent.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            # Assert
            assert result["success"] is False
            assert "Cannot resolve hostname" in result["message"]
            assert result["details"]["error_type"] == "dns"

    @pytest.mark.asyncio
    async def test_test_connection_no_auth_method(self, ssh_service):
        """Test SSH connection with no authentication method provided."""
        # Act
        result = await ssh_service.test_connection(
            host="test.example.com",
            port=22,
            username="testuser"
        )

        # Assert
        assert result["success"] is False
        assert result["message"] == "No authentication method provided"

    def test_load_private_key_rsa(self, ssh_service, mock_ssh_key):
        """Test loading RSA private key."""
        # Arrange
        mock_rsa_key = MagicMock(spec=paramiko.RSAKey)
        
        with patch("paramiko.RSAKey.from_private_key", return_value=mock_rsa_key):
            # Act
            result = ssh_service._load_private_key(mock_ssh_key)

            # Assert
            assert result == mock_rsa_key

    def test_load_private_key_unsupported_type(self, ssh_service):
        """Test loading unsupported key type."""
        # Arrange
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "unsupported"

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported key type: unsupported"):
            ssh_service._load_private_key(ssh_key)

    def test_load_private_key_invalid_format(self, ssh_service):
        """Test loading private key with invalid format."""
        # Arrange
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "rsa"
        ssh_key.encrypted_private_key = b"invalid key data"

        with patch("paramiko.RSAKey.from_private_key", side_effect=Exception("Invalid key")):
            # Act & Assert
            with pytest.raises(Exception, match="Invalid rsa key format"):
                ssh_service._load_private_key(ssh_key)

    @pytest.mark.asyncio
    async def test_get_host_key_success(self, ssh_service):
        """Test successful host key retrieval."""
        # Arrange
        mock_transport = MagicMock()
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-rsa"
        mock_host_key.get_fingerprint.return_value = bytes.fromhex("deadbeef")
        mock_host_key.get_base64.return_value = "AAAAB3NzaC1yc2E"
        
        mock_transport.get_remote_server_key.return_value = mock_host_key
        mock_transport.connect = MagicMock()
        mock_transport.close = MagicMock()

        with patch("paramiko.Transport", return_value=mock_transport):
            # Act
            result = await ssh_service.get_host_key("test.example.com", 22)

            # Assert
            assert result is not None
            assert result["type"] == "ssh-rsa"
            assert result["fingerprint"] == "deadbeef"
            assert result["base64"] == "AAAAB3NzaC1yc2E"

    @pytest.mark.asyncio
    async def test_get_host_key_failure(self, ssh_service):
        """Test host key retrieval failure."""
        # Arrange
        with patch("paramiko.Transport", side_effect=Exception("Connection failed")):
            # Act
            result = await ssh_service.get_host_key("test.example.com", 22)

            # Assert
            assert result is None

    def test_generate_key_pair_rsa(self, ssh_service):
        """Test RSA key pair generation."""
        # Arrange
        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-rsa"
        mock_key.get_base64.return_value = "AAAAB3NzaC1yc2E"
        mock_key.get_fingerprint.return_value = bytes.fromhex("deadbeef")
        
        mock_key_io = io.StringIO("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        
        with (
            patch("paramiko.RSAKey.generate", return_value=mock_key),
            patch("io.StringIO", return_value=mock_key_io)
        ):
            mock_key.write_private_key = MagicMock()
            
            # Act
            result = ssh_service.generate_key_pair("rsa", 2048, "test@example.com")

            # Assert
            assert result["key_type"] == "rsa"
            assert "ssh-rsa AAAAB3NzaC1yc2E test@example.com" == result["public_key"]
            assert result["fingerprint"] == "deadbeef"

    def test_generate_key_pair_ed25519(self, ssh_service):
        """Test Ed25519 key pair generation."""
        # Arrange
        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-ed25519"
        mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5"
        mock_key.get_fingerprint.return_value = bytes.fromhex("cafebabe")
        
        # Mock write_private_key to not actually write anything
        def mock_write_private_key(file_obj):
            file_obj.write("-----BEGIN OPENSSH PRIVATE KEY-----\ntest\n-----END OPENSSH PRIVATE KEY-----")
        
        mock_key.write_private_key = mock_write_private_key
        
        with patch("paramiko.Ed25519Key.generate", return_value=mock_key):
            # Act
            result = ssh_service.generate_key_pair("ed25519")

            # Assert
            assert result["key_type"] == "ed25519"
            assert result["public_key"] == "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5"
            assert result["fingerprint"] == "cafebabe"

    def test_generate_key_pair_unsupported(self, ssh_service):
        """Test key pair generation with unsupported type."""
        # Act & Assert
        with pytest.raises(Exception, match="Key generation failed"):
            ssh_service.generate_key_pair("unsupported")

    def test_validate_public_key_valid_rsa(self, ssh_service):
        """Test validation of valid RSA public key."""
        # Arrange
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"

        # Act
        result = ssh_service.validate_public_key(public_key)

        # Assert
        assert result is True

    def test_validate_public_key_valid_ed25519(self, ssh_service):
        """Test validation of valid Ed25519 public key."""
        # Arrange
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHzpNHFOH9nK7Dp8NI3V3dn9t3YVJ8E5GzaIGQAAAAA user@example.com"

        # Act
        result = ssh_service.validate_public_key(public_key)

        # Assert
        assert result is True

    def test_validate_public_key_invalid_format(self, ssh_service):
        """Test validation of invalid public key format."""
        # Arrange
        public_key = "invalid key format"

        # Act
        result = ssh_service.validate_public_key(public_key)

        # Assert
        assert result is False

    def test_validate_public_key_unsupported_type(self, ssh_service):
        """Test validation of unsupported key type."""
        # Arrange
        public_key = "ssh-unknown AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"

        # Act
        result = ssh_service.validate_public_key(public_key)

        # Assert
        assert result is False

    def test_validate_public_key_invalid_base64(self, ssh_service):
        """Test validation of public key with invalid base64 data."""
        # Arrange
        public_key = "ssh-rsa invalid_base64_data user@example.com"

        # Act
        result = ssh_service.validate_public_key(public_key)

        # Assert
        assert result is False

    def test_get_key_fingerprint_rsa(self, ssh_service):
        """Test getting fingerprint for RSA public key."""
        # Arrange
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"
        mock_key = MagicMock()
        mock_key.get_fingerprint.return_value = bytes.fromhex("deadbeef")

        with (
            patch("paramiko.RSAKey", return_value=mock_key),
            patch("base64.b64decode", return_value=b"mock_key_data")
        ):
            # Act
            result = ssh_service.get_key_fingerprint(public_key)

            # Assert
            assert result == "deadbeef"

    def test_get_key_fingerprint_ed25519(self, ssh_service):
        """Test getting fingerprint for Ed25519 public key."""
        # Arrange
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHzpNHFOH9nK7Dp8NI3V3dn9t3YVJ8E5GzaIGQAAAAA user@example.com"
        mock_key = MagicMock()
        mock_key.get_fingerprint.return_value = bytes.fromhex("cafebabe")

        with (
            patch("paramiko.Ed25519Key", return_value=mock_key),
            patch("base64.b64decode", return_value=b"mock_key_data")
        ):
            # Act
            result = ssh_service.get_key_fingerprint(public_key)

            # Assert
            assert result == "cafebabe"

    def test_get_key_fingerprint_invalid_format(self, ssh_service):
        """Test getting fingerprint for invalid public key format."""
        # Arrange
        public_key = "invalid key"

        # Act
        result = ssh_service.get_key_fingerprint(public_key)

        # Assert
        assert result is None

    def test_get_key_fingerprint_unsupported_type(self, ssh_service):
        """Test getting fingerprint for unsupported key type."""
        # Arrange
        public_key = "ssh-unknown AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"

        # Act
        result = ssh_service.get_key_fingerprint(public_key)

        # Assert
        assert result is None

    def test_get_key_fingerprint_exception(self, ssh_service):
        """Test getting fingerprint with exception during processing."""
        # Arrange
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"

        with patch("paramiko.RSAKey", side_effect=Exception("Key error")):
            # Act
            result = ssh_service.get_key_fingerprint(public_key)

            # Assert
            assert result is None

    def test_supported_key_types(self, ssh_service):
        """Test that all expected key types are supported."""
        # Act & Assert
        expected_types = {"rsa", "dsa", "ecdsa", "ed25519"}
        assert set(ssh_service.supported_key_types.keys()) == expected_types
        assert ssh_service.supported_key_types["rsa"] == paramiko.RSAKey
        assert ssh_service.supported_key_types["dsa"] == paramiko.DSSKey
        assert ssh_service.supported_key_types["ecdsa"] == paramiko.ECDSAKey
        assert ssh_service.supported_key_types["ed25519"] == paramiko.Ed25519Key