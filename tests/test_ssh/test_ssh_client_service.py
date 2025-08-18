"""
Comprehensive tests for SSH client service.

Tests all SSH client functionality including:
- Connection testing
- Key management
- Host key verification
- Key pair generation
- Public key validation
- Error handling
"""

import io
import socket
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import paramiko
import pytest

from app.models.ssh_profile import SSHKey
from app.services.ssh_client import SSHClientService


@pytest.mark.services
class TestSSHClientService:
    """Test SSH client service functionality."""

    @pytest.fixture
    def ssh_service(self):
        """Create SSH client service instance."""
        return SSHClientService()

    @pytest.fixture
    def mock_ssh_key(self):
        """Create mock SSH key for testing."""
        key = Mock(spec=SSHKey)
        key.key_type = "rsa"
        key.encrypted_private_key = b"""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdef...
-----END RSA PRIVATE KEY-----"""
        return key

    @pytest.fixture
    def mock_ssh_client(self):
        """Create mock SSH client."""
        client = Mock(spec=paramiko.SSHClient)
        transport = Mock()
        transport.remote_version = "OpenSSH_8.9"
        transport.get_cipher.return_value = ("aes128-ctr", "sha256")
        host_key = Mock()
        host_key.get_name.return_value = "ssh-rsa"
        transport.get_host_key.return_value = host_key
        client.get_transport.return_value = transport
        return client

    # Connection Testing Tests
    @pytest.mark.asyncio
    async def test_test_connection_success_with_key(self, ssh_service, mock_ssh_key):
        """Test successful SSH connection with private key."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_transport = Mock()
            mock_transport.remote_version = "OpenSSH_8.9"
            mock_transport.get_cipher.return_value = ("aes128-ctr", "sha256")
            mock_host_key = Mock()
            mock_host_key.get_name.return_value = "ssh-rsa"
            mock_transport.get_host_key.return_value = mock_host_key
            mock_client.get_transport.return_value = mock_transport

            # Mock successful command execution
            mock_stdout = Mock()
            mock_stdout.read.return_value = b"connection_test"
            mock_client.exec_command.return_value = (None, mock_stdout, None)

            # Mock private key loading
            with patch.object(ssh_service, "_load_private_key") as mock_load_key:
                mock_key = Mock()
                mock_load_key.return_value = mock_key

                result = await ssh_service.test_connection(
                    host="example.com",
                    port=22,
                    username="testuser",
                    ssh_key=mock_ssh_key,
                    timeout=30
                )

                assert result["success"] is True
                assert result["message"] == "Connection successful"
                assert result["server_info"]["version"] == "OpenSSH_8.9"
                assert result["server_info"]["cipher"] == "aes128-ctr"
                assert result["details"]["command_test"] == "passed"

    @pytest.mark.asyncio
    async def test_test_connection_success_with_password(self, ssh_service):
        """Test successful SSH connection with password."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_transport = Mock()
            mock_transport.remote_version = "OpenSSH_8.9"
            mock_transport.get_cipher.return_value = ("aes128-ctr", "sha256")
            mock_host_key = Mock()
            mock_host_key.get_name.return_value = "ssh-rsa"
            mock_transport.get_host_key.return_value = mock_host_key
            mock_client.get_transport.return_value = mock_transport

            # Mock successful command execution
            mock_stdout = Mock()
            mock_stdout.read.return_value = b"connection_test"
            mock_client.exec_command.return_value = (None, mock_stdout, None)

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=30
            )

            assert result["success"] is True
            assert result["message"] == "Connection successful"

    @pytest.mark.asyncio
    async def test_test_connection_no_auth_method(self, ssh_service):
        """Test connection failure when no authentication method provided."""
        result = await ssh_service.test_connection(
            host="example.com",
            port=22,
            username="testuser",
            timeout=30
        )

        assert result["success"] is False
        assert "No authentication method provided" in result["message"]

    @pytest.mark.asyncio
    async def test_test_connection_key_load_failure(self, ssh_service, mock_ssh_key):
        """Test connection failure when SSH key cannot be loaded."""
        with patch.object(ssh_service, "_load_private_key") as mock_load_key:
            mock_load_key.side_effect = Exception("Invalid key format")

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                ssh_key=mock_ssh_key,
                timeout=30
            )

            assert result["success"] is False
            assert "Failed to load SSH key" in result["message"]

    @pytest.mark.asyncio
    async def test_test_connection_authentication_failure(self, ssh_service):
        """Test authentication failure handling."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                password="wrongpass",
                timeout=30
            )

            assert result["success"] is False
            assert "Authentication failed" in result["message"]
            assert result["details"]["error_type"] == "authentication"

    @pytest.mark.asyncio
    async def test_test_connection_ssh_exception(self, ssh_service):
        """Test SSH protocol exception handling."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.connect.side_effect = paramiko.SSHException("SSH error")

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=30
            )

            assert result["success"] is False
            assert "SSH connection failed" in result["message"]
            assert result["details"]["error_type"] == "ssh_protocol"

    @pytest.mark.asyncio
    async def test_test_connection_timeout(self, ssh_service):
        """Test connection timeout handling."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.connect.side_effect = socket.timeout()

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=30
            )

            assert result["success"] is False
            assert "Connection timeout" in result["message"]
            assert result["details"]["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_test_connection_dns_failure(self, ssh_service):
        """Test DNS resolution failure handling."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.connect.side_effect = socket.gaierror("Name resolution failed")

            result = await ssh_service.test_connection(
                host="nonexistent.example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=30
            )

            assert result["success"] is False
            assert "Cannot resolve hostname" in result["message"]
            assert result["details"]["error_type"] == "dns"

    @pytest.mark.asyncio
    async def test_test_connection_refused(self, ssh_service):
        """Test connection refused handling."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.connect.side_effect = ConnectionRefusedError()

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=30
            )

            assert result["success"] is False
            assert "Connection refused" in result["message"]
            assert result["details"]["error_type"] == "connection_refused"

    @pytest.mark.asyncio
    async def test_test_connection_command_failure(self, ssh_service):
        """Test connection success but command execution failure."""
        with patch("paramiko.SSHClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_transport = Mock()
            mock_transport.remote_version = "OpenSSH_8.9"
            mock_client.get_transport.return_value = mock_transport

            # Mock command execution failure
            mock_client.exec_command.side_effect = Exception("Command failed")

            result = await ssh_service.test_connection(
                host="example.com",
                port=22,
                username="testuser",
                password="testpass",
                timeout=30
            )

            assert result["success"] is True  # Connection successful
            assert "command test failed" in result["message"].lower()
            assert result["details"]["command_test"] == "failed"

    # Private Key Loading Tests
    def test_load_private_key_rsa_success(self, ssh_service, mock_ssh_key):
        """Test successful RSA private key loading."""
        mock_ssh_key.key_type = "rsa"
        
        with patch("paramiko.RSAKey.from_private_key") as mock_from_key:
            mock_key = Mock()
            mock_from_key.return_value = mock_key

            result = ssh_service._load_private_key(mock_ssh_key)

            assert result == mock_key
            mock_from_key.assert_called_once()

    def test_load_private_key_unsupported_type(self, ssh_service, mock_ssh_key):
        """Test loading unsupported key type."""
        mock_ssh_key.key_type = "unsupported"

        with pytest.raises(ValueError, match="Unsupported key type"):
            ssh_service._load_private_key(mock_ssh_key)

    def test_load_private_key_invalid_format(self, ssh_service, mock_ssh_key):
        """Test loading invalid key format."""
        mock_ssh_key.key_type = "rsa"
        mock_ssh_key.encrypted_private_key = b"invalid key data"

        with patch("paramiko.RSAKey.from_private_key") as mock_from_key:
            mock_from_key.side_effect = Exception("Invalid key format")

            with pytest.raises(Exception, match="Invalid rsa key format"):
                ssh_service._load_private_key(mock_ssh_key)

    # Host Key Tests
    @pytest.mark.asyncio
    async def test_get_host_key_success(self, ssh_service):
        """Test successful host key retrieval."""
        with patch("paramiko.Transport") as mock_transport_class:
            mock_transport = mock_transport_class.return_value
            mock_host_key = Mock()
            mock_host_key.get_name.return_value = "ssh-rsa"
            mock_host_key.get_fingerprint.return_value = bytes.fromhex("1234567890abcdef")
            mock_host_key.get_base64.return_value = "AAAAB3NzaC1yc2EAAAA..."
            mock_transport.get_remote_server_key.return_value = mock_host_key

            result = await ssh_service.get_host_key("example.com", 22, 10)

            assert result is not None
            assert result["type"] == "ssh-rsa"
            assert result["fingerprint"] == "1234567890abcdef"
            assert result["base64"] == "AAAAB3NzaC1yc2EAAAA..."

    @pytest.mark.asyncio
    async def test_get_host_key_failure(self, ssh_service):
        """Test host key retrieval failure."""
        with patch("paramiko.Transport") as mock_transport_class:
            mock_transport_class.side_effect = Exception("Connection failed")

            result = await ssh_service.get_host_key("example.com", 22, 10)

            assert result is None

    # Key Generation Tests
    def test_generate_key_pair_rsa(self, ssh_service):
        """Test RSA key pair generation."""
        with patch("paramiko.RSAKey.generate") as mock_generate:
            mock_key = Mock()
            mock_key.get_name.return_value = "ssh-rsa"
            mock_key.get_base64.return_value = "AAAAB3NzaC1yc2EAAAA..."
            mock_key.get_fingerprint.return_value = bytes.fromhex("1234567890abcdef")
            mock_key.write_private_key = Mock()
            mock_generate.return_value = mock_key

            # Mock the private key writing
            def mock_write_private_key(file_obj):
                file_obj.write("-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n")
            
            mock_key.write_private_key.side_effect = mock_write_private_key

            result = ssh_service.generate_key_pair("rsa", 2048, "test@example.com")

            assert result["key_type"] == "rsa"
            assert "-----BEGIN RSA PRIVATE KEY-----" in result["private_key"]
            assert result["public_key"].startswith("ssh-rsa AAAAB3NzaC1yc2EAAAA...")
            assert result["fingerprint"] == "1234567890abcdef"

    def test_generate_key_pair_ecdsa(self, ssh_service):
        """Test ECDSA key pair generation."""
        with patch("paramiko.ECDSAKey.generate") as mock_generate:
            mock_key = Mock()
            mock_key.get_name.return_value = "ecdsa-sha2-nistp256"
            mock_key.get_base64.return_value = "AAAAE2VjZHNhLXNoYTItbmlzdHA..."
            mock_key.get_fingerprint.return_value = bytes.fromhex("abcdef1234567890")
            mock_key.write_private_key = Mock()
            mock_generate.return_value = mock_key

            def mock_write_private_key(file_obj):
                file_obj.write("-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n")
            
            mock_key.write_private_key.side_effect = mock_write_private_key

            result = ssh_service.generate_key_pair("ecdsa")

            assert result["key_type"] == "ecdsa"
            assert "-----BEGIN EC PRIVATE KEY-----" in result["private_key"]
            assert result["public_key"].startswith("ecdsa-sha2-nistp256")

    def test_generate_key_pair_ed25519(self, ssh_service):
        """Test Ed25519 key pair generation."""
        with patch("paramiko.Ed25519Key.generate") as mock_generate:
            mock_key = Mock()
            mock_key.get_name.return_value = "ssh-ed25519"
            mock_key.get_base64.return_value = "AAAAC3NzaC1lZDI1NTE5AAAA..."
            mock_key.get_fingerprint.return_value = bytes.fromhex("fedcba0987654321")
            mock_key.write_private_key = Mock()
            mock_generate.return_value = mock_key

            def mock_write_private_key(file_obj):
                file_obj.write("-----BEGIN OPENSSH PRIVATE KEY-----\n...\n-----END OPENSSH PRIVATE KEY-----\n")
            
            mock_key.write_private_key.side_effect = mock_write_private_key

            result = ssh_service.generate_key_pair("ed25519")

            assert result["key_type"] == "ed25519"
            assert result["public_key"].startswith("ssh-ed25519")

    def test_generate_key_pair_unsupported_type(self, ssh_service):
        """Test key generation with unsupported type."""
        with pytest.raises(Exception, match="Key generation failed"):
            ssh_service.generate_key_pair("unsupported")

    def test_generate_key_pair_generation_failure(self, ssh_service):
        """Test key generation failure."""
        with patch("paramiko.RSAKey.generate") as mock_generate:
            mock_generate.side_effect = Exception("Generation failed")

            with pytest.raises(Exception, match="Key generation failed"):
                ssh_service.generate_key_pair("rsa")

    # Public Key Validation Tests
    def test_validate_public_key_rsa_valid(self, ssh_service):
        """Test validation of valid RSA public key."""
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... user@example.com"
        
        with patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            
            result = ssh_service.validate_public_key(public_key)
            assert result is True

    def test_validate_public_key_ecdsa_valid(self, ssh_service):
        """Test validation of valid ECDSA public key."""
        public_key = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHA... user@example.com"
        
        with patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            
            result = ssh_service.validate_public_key(public_key)
            assert result is True

    def test_validate_public_key_ed25519_valid(self, ssh_service):
        """Test validation of valid Ed25519 public key."""
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... user@example.com"
        
        with patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            
            result = ssh_service.validate_public_key(public_key)
            assert result is True

    def test_validate_public_key_invalid_format(self, ssh_service):
        """Test validation of invalid public key format."""
        public_key = "invalid"
        
        result = ssh_service.validate_public_key(public_key)
        assert result is False

    def test_validate_public_key_unsupported_type(self, ssh_service):
        """Test validation of unsupported key type."""
        public_key = "unsupported-type AAAAB3NzaC1yc2EAAAA... user@example.com"
        
        result = ssh_service.validate_public_key(public_key)
        assert result is False

    def test_validate_public_key_invalid_base64(self, ssh_service):
        """Test validation with invalid base64 data."""
        public_key = "ssh-rsa invalid_base64_data user@example.com"
        
        result = ssh_service.validate_public_key(public_key)
        assert result is False

    # Key Fingerprint Tests
    def test_get_key_fingerprint_rsa(self, ssh_service):
        """Test getting fingerprint for RSA key."""
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC user@example.com"
        
        with patch("app.services.ssh_client.RSAKey") as mock_rsa_key, \
             patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            mock_key_instance = Mock()
            mock_key_instance.get_fingerprint.return_value = bytes.fromhex("1234567890abcdef")
            mock_rsa_key.return_value = mock_key_instance
            
            result = ssh_service.get_key_fingerprint(public_key)
            assert result == "1234567890abcdef"

    def test_get_key_fingerprint_ecdsa(self, ssh_service):
        """Test getting fingerprint for ECDSA key."""
        public_key = "ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHA user@example.com"
        
        with patch("app.services.ssh_client.ECDSAKey") as mock_ecdsa_key, \
             patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            mock_key_instance = Mock()
            mock_key_instance.get_fingerprint.return_value = bytes.fromhex("abcdef1234567890")
            mock_ecdsa_key.return_value = mock_key_instance
            
            result = ssh_service.get_key_fingerprint(public_key)
            assert result == "abcdef1234567890"

    def test_get_key_fingerprint_ed25519(self, ssh_service):
        """Test getting fingerprint for Ed25519 key."""
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA user@example.com"
        
        with patch("app.services.ssh_client.Ed25519Key") as mock_ed25519_key, \
             patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            mock_key_instance = Mock()
            mock_key_instance.get_fingerprint.return_value = bytes.fromhex("fedcba0987654321")
            mock_ed25519_key.return_value = mock_key_instance
            
            result = ssh_service.get_key_fingerprint(public_key)
            assert result == "fedcba0987654321"

    def test_get_key_fingerprint_invalid_format(self, ssh_service):
        """Test getting fingerprint for invalid key format."""
        public_key = "invalid"
        
        result = ssh_service.get_key_fingerprint(public_key)
        assert result is None

    def test_get_key_fingerprint_unsupported_type(self, ssh_service):
        """Test getting fingerprint for unsupported key type."""
        public_key = "unsupported-type AAAAB3NzaC1yc2EAAAA... user@example.com"
        
        with patch("base64.b64decode") as mock_decode:
            mock_decode.return_value = b"valid_key_data"
            
            result = ssh_service.get_key_fingerprint(public_key)
            assert result is None

    def test_get_key_fingerprint_exception(self, ssh_service):
        """Test getting fingerprint when exception occurs."""
        public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... user@example.com"
        
        with patch("base64.b64decode") as mock_decode:
            mock_decode.side_effect = Exception("Decode error")
            
            result = ssh_service.get_key_fingerprint(public_key)
            assert result is None

    # Service Attributes Tests
    def test_supported_key_types(self, ssh_service):
        """Test that service supports expected key types."""
        expected_types = {"rsa", "dsa", "ecdsa", "ed25519"}
        assert set(ssh_service.supported_key_types.keys()) == expected_types
        
        # Test that key classes are correct
        assert ssh_service.supported_key_types["rsa"] == paramiko.RSAKey
        assert ssh_service.supported_key_types["dsa"] == paramiko.DSSKey
        assert ssh_service.supported_key_types["ecdsa"] == paramiko.ECDSAKey
        assert ssh_service.supported_key_types["ed25519"] == paramiko.Ed25519Key