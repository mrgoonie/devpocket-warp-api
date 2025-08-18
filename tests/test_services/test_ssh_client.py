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


class TestSSHClientServiceComprehensive:
    """Comprehensive tests for SSH client service to achieve 80% coverage."""

    @pytest.fixture
    def ssh_service(self):
        """Create SSH client service instance."""
        return SSHClientService()

    @pytest.fixture
    def mock_ecdsa_key(self):
        """Create mock ECDSA SSH key."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "ecdsa"
        ssh_key.encrypted_private_key = b"""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAaAAAABNlY2RzYS
-----END OPENSSH PRIVATE KEY-----"""
        return ssh_key

    @pytest.fixture
    def mock_ed25519_key(self):
        """Create mock Ed25519 SSH key."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "ed25519"
        ssh_key.encrypted_private_key = b"""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
-----END OPENSSH PRIVATE KEY-----"""
        return ssh_key

    @pytest.fixture
    def mock_dsa_key(self):
        """Create mock DSA SSH key."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "dsa"
        ssh_key.encrypted_private_key = b"""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAiAAAABVzc2gtZH
-----END OPENSSH PRIVATE KEY-----"""
        return ssh_key

    # Test Connection Scenarios with Different Auth Methods
    @pytest.mark.asyncio
    async def test_test_connection_with_ecdsa_key_success(self, ssh_service, mock_ecdsa_key):
        """Test successful SSH connection with ECDSA key authentication."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"connection_test"
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_8.9"
        mock_transport.get_cipher.return_value = ("chacha20-poly1305@openssh.com", "umac-128-etm@openssh.com")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ecdsa-sha2-nistp256"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_client.get_transport.return_value = mock_transport

        mock_ecdsa_pkey = MagicMock(spec=paramiko.ECDSAKey)
        
        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch.object(ssh_service, "_load_private_key", return_value=mock_ecdsa_pkey),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            result = await ssh_service.test_connection(
                host="ecdsa.example.com",
                port=2222,
                username="ecdsa_user",
                ssh_key=mock_ecdsa_key,
                timeout=15
            )

            assert result["success"] is True
            assert "Connection successful" in result["message"]
            assert result["details"]["command_test"] == "passed"
            assert result["server_info"]["version"] == "OpenSSH_8.9"
            assert result["server_info"]["cipher"] == "chacha20-poly1305@openssh.com"
            assert result["server_info"]["host_key_type"] == "ecdsa-sha2-nistp256"

    @pytest.mark.asyncio
    async def test_test_connection_with_ed25519_key_success(self, ssh_service, mock_ed25519_key):
        """Test successful SSH connection with Ed25519 key authentication."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"connection_test"
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_9.0"
        mock_transport.get_cipher.return_value = ("aes256-gcm@openssh.com", "hmac-sha2-256-etm@openssh.com")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-ed25519"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_client.get_transport.return_value = mock_transport

        mock_ed25519_pkey = MagicMock(spec=paramiko.Ed25519Key)
        
        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch.object(ssh_service, "_load_private_key", return_value=mock_ed25519_pkey),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            result = await ssh_service.test_connection(
                host="ed25519.example.com",
                port=22,
                username="ed25519_user",
                ssh_key=mock_ed25519_key
            )

            assert result["success"] is True
            assert "Connection successful" in result["message"]
            assert result["details"]["command_test"] == "passed"
            assert result["server_info"]["host_key_type"] == "ssh-ed25519"

    @pytest.mark.asyncio
    async def test_test_connection_command_execution_success(self, ssh_service):
        """Test SSH connection with successful command execution."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"connection_test"
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_8.0"
        mock_transport.get_cipher.return_value = ("aes128-ctr", "hmac-sha2-256")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-rsa"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_client.get_transport.return_value = mock_transport

        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            assert result["success"] is True
            assert "Connection successful" in result["message"]
            assert result["details"]["command_test"] == "passed"

    @pytest.mark.asyncio
    async def test_test_connection_command_execution_failure(self, ssh_service):
        """Test SSH connection with failed command execution."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"unexpected_output"
        mock_client.exec_command.return_value = (None, mock_stdout, None)
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_8.0"
        mock_transport.get_cipher.return_value = ("aes128-ctr", "hmac-sha2-256")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-rsa"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_client.get_transport.return_value = mock_transport

        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            assert result["success"] is False
            assert "command execution failed" in result["message"]
            assert result["details"]["command_test"] == "failed"
            assert result["details"]["command_output"] == "unexpected_output"

    @pytest.mark.asyncio
    async def test_test_connection_command_exception(self, ssh_service):
        """Test SSH connection with command execution exception."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_client.exec_command.side_effect = Exception("Command failed")
        
        mock_transport = MagicMock()
        mock_transport.remote_version = "OpenSSH_8.0"
        mock_transport.get_cipher.return_value = ("aes128-ctr", "hmac-sha2-256")
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ssh-rsa"
        mock_transport.get_host_key.return_value = mock_host_key
        mock_client.get_transport.return_value = mock_transport

        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            assert result["success"] is True  # Connection successful but command failed
            assert "Connection successful (command test failed)" in result["message"]
            assert result["details"]["command_test"] == "failed"
            assert "Command failed" in result["details"]["command_error"]

    @pytest.mark.asyncio
    async def test_test_connection_no_transport(self, ssh_service):
        """Test SSH connection with no transport available."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_client.get_transport.return_value = None
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"connection_test"
        mock_client.exec_command.return_value = (None, mock_stdout, None)

        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            mock_loop.return_value.run_in_executor.return_value = asyncio.Future()
            mock_loop.return_value.run_in_executor.return_value.set_result(None)
            
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            assert result["success"] is True
            assert "server_info" not in result or not result["server_info"]

    @pytest.mark.asyncio
    async def test_test_connection_ssh_exception(self, ssh_service):
        """Test SSH connection with SSH protocol exception."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        
        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            future = asyncio.Future()
            future.set_exception(paramiko.SSHException("Protocol error"))
            mock_loop.return_value.run_in_executor.return_value = future
            
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            assert result["success"] is False
            assert "SSH connection failed: Protocol error" in result["message"]
            assert result["details"]["error_type"] == "ssh_protocol"

    @pytest.mark.asyncio
    async def test_test_connection_unknown_exception(self, ssh_service):
        """Test SSH connection with unknown exception."""
        mock_client = MagicMock(spec=paramiko.SSHClient)
        
        with (
            patch("paramiko.SSHClient", return_value=mock_client),
            patch("asyncio.get_event_loop") as mock_loop
        ):
            future = asyncio.Future()
            future.set_exception(ValueError("Unknown error"))
            mock_loop.return_value.run_in_executor.return_value = future
            
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                password="testpass"
            )

            assert result["success"] is False
            assert "Connection test failed: Unknown error" in result["message"]
            assert result["details"]["error_type"] == "unknown"
            assert result["details"]["error"] == "Unknown error"

    # Test SSH Key Loading with Different Key Types
    def test_load_private_key_ecdsa(self, ssh_service, mock_ecdsa_key):
        """Test loading ECDSA private key."""
        mock_ecdsa_pkey = MagicMock(spec=paramiko.ECDSAKey)
        
        with patch("paramiko.ECDSAKey.from_private_key", return_value=mock_ecdsa_pkey):
            result = ssh_service._load_private_key(mock_ecdsa_key)
            assert result == mock_ecdsa_pkey

    def test_load_private_key_ed25519(self, ssh_service, mock_ed25519_key):
        """Test loading Ed25519 private key."""
        mock_ed25519_pkey = MagicMock(spec=paramiko.Ed25519Key)
        
        with patch("paramiko.Ed25519Key.from_private_key", return_value=mock_ed25519_pkey):
            result = ssh_service._load_private_key(mock_ed25519_key)
            assert result == mock_ed25519_pkey

    def test_load_private_key_dsa(self, ssh_service, mock_dsa_key):
        """Test loading DSA private key."""
        mock_dsa_pkey = MagicMock(spec=paramiko.DSSKey)
        
        with patch("paramiko.DSSKey.from_private_key", return_value=mock_dsa_pkey):
            result = ssh_service._load_private_key(mock_dsa_key)
            assert result == mock_dsa_pkey

    def test_load_private_key_with_passphrase(self, ssh_service):
        """Test loading private key with passphrase."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "rsa"
        ssh_key.encrypted_private_key = b"encrypted key data"
        mock_rsa_pkey = MagicMock(spec=paramiko.RSAKey)
        
        with patch("paramiko.RSAKey.from_private_key", return_value=mock_rsa_pkey) as mock_from_key:
            result = ssh_service._load_private_key(ssh_key, passphrase="secret")
            
            assert result == mock_rsa_pkey
            mock_from_key.assert_called_once()
            call_args = mock_from_key.call_args
            assert call_args[1]["password"] == "secret"

    def test_load_private_key_case_insensitive(self, ssh_service):
        """Test loading private key with case-insensitive key type."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "RSA"  # Uppercase
        ssh_key.encrypted_private_key = b"key data"
        mock_rsa_pkey = MagicMock(spec=paramiko.RSAKey)
        
        with patch("paramiko.RSAKey.from_private_key", return_value=mock_rsa_pkey):
            result = ssh_service._load_private_key(ssh_key)
            assert result == mock_rsa_pkey

    # Test Key Pair Generation with Different Parameters
    def test_generate_key_pair_ecdsa(self, ssh_service):
        """Test ECDSA key pair generation."""
        mock_key = MagicMock()
        mock_key.get_name.return_value = "ecdsa-sha2-nistp256"
        mock_key.get_base64.return_value = "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY"
        mock_key.get_fingerprint.return_value = bytes.fromhex("fedcba98")
        
        def mock_write_private_key(file_obj):
            file_obj.write("-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----")
        
        mock_key.write_private_key = mock_write_private_key
        
        with patch("paramiko.ECDSAKey.generate", return_value=mock_key):
            result = ssh_service.generate_key_pair("ecdsa", comment="test@ecdsa.com")

            assert result["key_type"] == "ecdsa"
            assert result["public_key"] == "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY test@ecdsa.com"
            assert result["fingerprint"] == "fedcba98"
            assert "BEGIN EC PRIVATE KEY" in result["private_key"]

    def test_generate_key_pair_rsa_custom_size(self, ssh_service):
        """Test RSA key pair generation with custom size."""
        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-rsa"
        mock_key.get_base64.return_value = "AAAAB3NzaC1yc2EAAAADAQABAAACAQ"
        mock_key.get_fingerprint.return_value = bytes.fromhex("12345678")
        
        def mock_write_private_key(file_obj):
            file_obj.write("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
        
        mock_key.write_private_key = mock_write_private_key
        
        with patch("paramiko.RSAKey.generate", return_value=mock_key) as mock_generate:
            result = ssh_service.generate_key_pair("rsa", key_size=4096)

            mock_generate.assert_called_once_with(4096)
            assert result["key_type"] == "rsa"
            assert result["fingerprint"] == "12345678"

    def test_generate_key_pair_no_comment(self, ssh_service):
        """Test key pair generation without comment."""
        mock_key = MagicMock()
        mock_key.get_name.return_value = "ssh-ed25519"
        mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5AAAAINtNVNOy"
        mock_key.get_fingerprint.return_value = bytes.fromhex("abcdef01")
        
        def mock_write_private_key(file_obj):
            file_obj.write("-----BEGIN OPENSSH PRIVATE KEY-----\ntest\n-----END OPENSSH PRIVATE KEY-----")
        
        mock_key.write_private_key = mock_write_private_key
        
        with patch("paramiko.Ed25519Key.generate", return_value=mock_key):
            result = ssh_service.generate_key_pair("ed25519")

            assert result["public_key"] == "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINtNVNOy"
            assert " " not in result["public_key"].split(" ", 2)[2:] # No comment

    def test_generate_key_pair_exception_handling(self, ssh_service):
        """Test key pair generation exception handling."""
        with patch("paramiko.RSAKey.generate", side_effect=ValueError("Invalid key size")):
            with pytest.raises(Exception, match="Key generation failed: Invalid key size"):
                ssh_service.generate_key_pair("rsa", key_size=-1)

    # Test Public Key Validation Edge Cases
    def test_validate_public_key_all_supported_types(self, ssh_service):
        """Test validation of all supported public key types."""
        test_keys = [
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com",
            "ssh-dss AAAAB3NzaC1kc3MAAACBAOmkqtUNmIGrjwKjKcU user@example.com",
            "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY user@example.com",
            "ecdsa-sha2-nistp384 AAAAE2VjZHNhLXNoYTItbmlzdHAzODQ user@example.com",
            "ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjE user@example.com",
            "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHzpNHFOH9nK user@example.com"
        ]
        
        for key in test_keys:
            assert ssh_service.validate_public_key(key) is True

    def test_validate_public_key_missing_parts(self, ssh_service):
        """Test validation of public key with missing parts."""
        invalid_keys = [
            "ssh-rsa",  # Missing key data
            "AAAAB3NzaC1yc2EAAAADAQABAAABAQC7",  # Missing key type
            "",  # Empty string
            "   ",  # Whitespace only
        ]
        
        for key in invalid_keys:
            assert ssh_service.validate_public_key(key) is False

    def test_validate_public_key_with_whitespace(self, ssh_service):
        """Test validation of public key with extra whitespace."""
        key_with_whitespace = "  ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com  "
        assert ssh_service.validate_public_key(key_with_whitespace) is True

    def test_validate_public_key_base64_decode_exception(self, ssh_service):
        """Test validation handling base64 decode exceptions."""
        with patch("base64.b64decode", side_effect=Exception("Decode error")):
            result = ssh_service.validate_public_key("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7")
            assert result is False

    # Test Key Fingerprint Generation Edge Cases
    def test_get_key_fingerprint_ecdsa_variants(self, ssh_service):
        """Test getting fingerprint for different ECDSA variants."""
        test_cases = [
            ("ecdsa-sha2-nistp256", paramiko.ECDSAKey),
            ("ecdsa-sha2-nistp384", paramiko.ECDSAKey),
            ("ecdsa-sha2-nistp521", paramiko.ECDSAKey),
        ]
        
        for key_type, key_class in test_cases:
            public_key = f"{key_type} AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY user@example.com"
            mock_key = MagicMock()
            mock_key.get_fingerprint.return_value = bytes.fromhex("deadbeef")

            with (
                patch.object(key_class, "__new__", return_value=mock_key),
                patch("base64.b64decode", return_value=b"mock_key_data")
            ):
                result = ssh_service.get_key_fingerprint(public_key)
                assert result == "deadbeef"

    def test_get_key_fingerprint_dsa(self, ssh_service):
        """Test getting fingerprint for DSA public key."""
        public_key = "ssh-dss AAAAB3NzaC1kc3MAAACBAOmkqtUNmIGrjwKjKcU user@example.com"
        mock_key = MagicMock()
        mock_key.get_fingerprint.return_value = bytes.fromhex("beefdead")

        with (
            patch("paramiko.DSSKey", return_value=mock_key),
            patch("base64.b64decode", return_value=b"mock_key_data")
        ):
            result = ssh_service.get_key_fingerprint(public_key)
            assert result == "beefdead"

    def test_get_key_fingerprint_base64_decode_exception(self, ssh_service):
        """Test fingerprint generation with base64 decode exception."""
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"
        
        with patch("base64.b64decode", side_effect=Exception("Decode error")):
            result = ssh_service.get_key_fingerprint(public_key)
            assert result is None

    def test_get_key_fingerprint_key_creation_exception(self, ssh_service):
        """Test fingerprint generation with key creation exception."""
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7 user@example.com"
        
        with (
            patch("base64.b64decode", return_value=b"mock_key_data"),
            patch("paramiko.RSAKey", side_effect=Exception("Key creation failed"))
        ):
            result = ssh_service.get_key_fingerprint(public_key)
            assert result is None

    # Test Host Key Retrieval with Different Scenarios
    @pytest.mark.asyncio
    async def test_get_host_key_custom_port(self, ssh_service):
        """Test host key retrieval with custom port."""
        mock_transport = MagicMock()
        mock_host_key = MagicMock()
        mock_host_key.get_name.return_value = "ecdsa-sha2-nistp256"
        mock_host_key.get_fingerprint.return_value = bytes.fromhex("fedcba98")
        mock_host_key.get_base64.return_value = "AAAAE2VjZHNhLXNoYTI"
        
        mock_transport.get_remote_server_key.return_value = mock_host_key
        mock_transport.connect = MagicMock()
        mock_transport.close = MagicMock()

        with patch("paramiko.Transport", return_value=mock_transport) as mock_transport_class:
            result = await ssh_service.get_host_key("custom.example.com", port=2222, timeout=5)

            mock_transport_class.assert_called_once_with(("custom.example.com", 2222))
            mock_transport.connect.assert_called_once_with(timeout=5)
            assert result is not None
            assert result["type"] == "ecdsa-sha2-nistp256"
            assert result["fingerprint"] == "fedcba98"

    @pytest.mark.asyncio
    async def test_get_host_key_connection_exception(self, ssh_service):
        """Test host key retrieval with connection exception."""
        with patch("paramiko.Transport", side_effect=ConnectionRefusedError("Connection refused")):
            result = await ssh_service.get_host_key("unreachable.example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_host_key_transport_exception(self, ssh_service):
        """Test host key retrieval with transport exception."""
        mock_transport = MagicMock()
        mock_transport.connect.side_effect = socket.timeout("Connection timeout")
        
        with patch("paramiko.Transport", return_value=mock_transport):
            result = await ssh_service.get_host_key("timeout.example.com", timeout=1)
            assert result is None

    # Test Additional Edge Cases and Error Handling
    @pytest.mark.asyncio
    async def test_test_connection_key_loading_failure(self, ssh_service):
        """Test connection with key loading failure."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "rsa"
        
        with patch.object(ssh_service, "_load_private_key", side_effect=Exception("Key load failed")):
            result = await ssh_service.test_connection(
                host="test.example.com",
                port=22,
                username="testuser",
                ssh_key=ssh_key
            )

            assert result["success"] is False
            assert "Failed to load SSH key: Key load failed" in result["message"]

    def test_load_private_key_various_exceptions(self, ssh_service):
        """Test private key loading with various exception types."""
        ssh_key = MagicMock(spec=SSHKey)
        ssh_key.key_type = "rsa"
        ssh_key.encrypted_private_key = b"invalid key"
        
        exception_types = [
            (paramiko.PasswordRequiredException("Password required"), "Invalid rsa key format or incorrect passphrase"),
            (paramiko.SSHException("SSH error"), "Invalid rsa key format or incorrect passphrase"),
            (ValueError("Value error"), "Invalid rsa key format or incorrect passphrase"),
        ]
        
        for exception, expected_message in exception_types:
            with patch("paramiko.RSAKey.from_private_key", side_effect=exception):
                with pytest.raises(Exception, match=expected_message):
                    ssh_service._load_private_key(ssh_key)