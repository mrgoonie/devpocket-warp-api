"""
SSH client service for DevPocket API.

Handles SSH connections, key management, and connection testing.
"""

import asyncio
import io
import socket
from typing import Optional, Dict, Any
import paramiko
from paramiko import SSHClient, AutoAddPolicy, RSAKey, ECDSAKey, Ed25519Key, DSSKey

from app.core.logging import logger
from app.models.ssh_profile import SSHKey


class SSHClientService:
    """Service for SSH client operations."""

    def __init__(self):
        """Initialize SSH client service."""
        self.supported_key_types = {
            'rsa': RSAKey,
            'dsa': DSSKey,
            'ecdsa': ECDSAKey,
            'ed25519': Ed25519Key,
        }

    async def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        ssh_key: Optional[SSHKey] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Test SSH connection to a remote host.
        
        Args:
            host: Remote host address
            port: SSH port
            username: SSH username
            ssh_key: SSH key for authentication (optional)
            password: Password for authentication (optional)
            timeout: Connection timeout in seconds
            
        Returns:
            Dict containing connection test results
        """
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        
        result = {
            "success": False,
            "message": "",
            "details": {},
            "server_info": {}
        }
        
        try:
            # Prepare authentication parameters
            connect_params = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
                "banner_timeout": timeout,
                "auth_timeout": timeout,
            }
            
            # Add authentication method
            if ssh_key:
                try:
                    # Load the private key
                    private_key = self._load_private_key(ssh_key)
                    connect_params["pkey"] = private_key
                    auth_method = "publickey"
                except Exception as e:
                    logger.error(f"Failed to load SSH key: {e}")
                    result["message"] = f"Failed to load SSH key: {str(e)}"
                    return result
                    
            elif password:
                connect_params["password"] = password
                auth_method = "password"
            else:
                result["message"] = "No authentication method provided"
                return result

            # Attempt connection
            logger.info(f"Testing SSH connection to {username}@{host}:{port} using {auth_method}")
            
            # Run connection test in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: client.connect(**connect_params)
            )
            
            # Get server information
            transport = client.get_transport()
            if transport:
                server_version = transport.remote_version
                server_cipher = transport.get_cipher()[0] if transport.get_cipher() else "unknown"
                
                result["server_info"] = {
                    "version": server_version,
                    "cipher": server_cipher,
                    "host_key_type": transport.get_host_key().get_name(),
                }
            
            # Test basic command execution
            try:
                stdin, stdout, stderr = client.exec_command("echo 'connection_test'", timeout=10)
                test_output = stdout.read().decode().strip()
                
                if test_output == "connection_test":
                    result["success"] = True
                    result["message"] = "Connection successful"
                    result["details"]["command_test"] = "passed"
                else:
                    result["message"] = "Connection established but command execution failed"
                    result["details"]["command_test"] = "failed"
                    result["details"]["command_output"] = test_output
                    
            except Exception as cmd_error:
                # Connection successful but command failed
                logger.warning(f"SSH command test failed: {cmd_error}")
                result["success"] = True  # Connection itself is successful
                result["message"] = "Connection successful (command test failed)"
                result["details"]["command_test"] = "failed"
                result["details"]["command_error"] = str(cmd_error)
                
        except paramiko.AuthenticationException as e:
            logger.warning(f"SSH authentication failed for {username}@{host}: {e}")
            result["message"] = f"Authentication failed: {str(e)}"
            result["details"]["error_type"] = "authentication"
            
        except paramiko.SSHException as e:
            logger.warning(f"SSH connection failed for {host}: {e}")
            result["message"] = f"SSH connection failed: {str(e)}"
            result["details"]["error_type"] = "ssh_protocol"
            
        except socket.timeout:
            logger.warning(f"SSH connection timeout for {host}:{port}")
            result["message"] = f"Connection timeout after {timeout} seconds"
            result["details"]["error_type"] = "timeout"
            
        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed for {host}: {e}")
            result["message"] = f"Cannot resolve hostname: {host}"
            result["details"]["error_type"] = "dns"
            
        except ConnectionRefusedError:
            logger.warning(f"Connection refused for {host}:{port}")
            result["message"] = f"Connection refused. Is SSH server running on port {port}?"
            result["details"]["error_type"] = "connection_refused"
            
        except Exception as e:
            logger.error(f"Unexpected error testing SSH connection: {e}")
            result["message"] = f"Connection test failed: {str(e)}"
            result["details"]["error_type"] = "unknown"
            result["details"]["error"] = str(e)
            
        finally:
            try:
                client.close()
            except Exception:
                pass  # Ignore cleanup errors
                
        return result

    def _load_private_key(self, ssh_key: SSHKey, passphrase: Optional[str] = None) -> paramiko.PKey:
        """
        Load a private key from SSHKey model.
        
        Args:
            ssh_key: SSH key model instance
            passphrase: Optional passphrase for encrypted keys
            
        Returns:
            Paramiko private key object
            
        Raises:
            Exception: If key cannot be loaded or format is invalid
        """
        key_type = ssh_key.key_type.lower()
        
        if key_type not in self.supported_key_types:
            raise ValueError(f"Unsupported key type: {key_type}")
        
        key_class = self.supported_key_types[key_type]
        
        try:
            # Decrypt the private key (simplified - use proper encryption in production)
            private_key_data = ssh_key.encrypted_private_key.decode('utf-8')
            key_file = io.StringIO(private_key_data)
            
            # Load the key with optional passphrase
            private_key = key_class.from_private_key(key_file, password=passphrase)
            
            return private_key
            
        except Exception as e:
            logger.error(f"Failed to load {key_type} key: {e}")
            raise Exception(f"Invalid {key_type} key format or incorrect passphrase")

    async def get_host_key(self, host: str, port: int = 22, timeout: int = 10) -> Optional[Dict[str, str]]:
        """
        Get the host key for a remote SSH server.
        
        Args:
            host: Remote host address
            port: SSH port
            timeout: Connection timeout
            
        Returns:
            Dict with host key information or None if failed
        """
        try:
            transport = paramiko.Transport((host, port))
            transport.connect(timeout=timeout)
            
            host_key = transport.get_remote_server_key()
            
            result = {
                "type": host_key.get_name(),
                "fingerprint": host_key.get_fingerprint().hex(),
                "base64": host_key.get_base64()
            }
            
            transport.close()
            return result
            
        except Exception as e:
            logger.error(f"Failed to get host key for {host}:{port}: {e}")
            return None

    def generate_key_pair(
        self,
        key_type: str = "rsa",
        key_size: int = 2048,
        comment: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate a new SSH key pair.
        
        Args:
            key_type: Type of key to generate (rsa, ecdsa, ed25519)
            key_size: Key size (for RSA keys)
            comment: Optional comment for the key
            
        Returns:
            Dict containing private_key, public_key, and fingerprint
        """
        try:
            if key_type == "rsa":
                key = RSAKey.generate(key_size)
            elif key_type == "ecdsa":
                key = ECDSAKey.generate()
            elif key_type == "ed25519":
                key = Ed25519Key.generate()
            else:
                raise ValueError(f"Unsupported key type: {key_type}")

            # Get private key
            private_key_io = io.StringIO()
            key.write_private_key(private_key_io)
            private_key = private_key_io.getvalue()

            # Get public key
            public_key = f"{key.get_name()} {key.get_base64()}"
            if comment:
                public_key += f" {comment}"

            # Get fingerprint
            fingerprint = key.get_fingerprint().hex()

            return {
                "private_key": private_key,
                "public_key": public_key,
                "fingerprint": fingerprint,
                "key_type": key_type
            }

        except Exception as e:
            logger.error(f"Failed to generate {key_type} key pair: {e}")
            raise Exception(f"Key generation failed: {str(e)}")

    def validate_public_key(self, public_key: str) -> bool:
        """
        Validate a public key format.
        
        Args:
            public_key: Public key string
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to parse the public key
            parts = public_key.strip().split()
            if len(parts) < 2:
                return False

            key_type = parts[0]
            key_data = parts[1]

            # Check if key type is supported
            if key_type not in ['ssh-rsa', 'ssh-dss', 'ecdsa-sha2-nistp256', 
                              'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521', 'ssh-ed25519']:
                return False

            # Try to decode the base64 data
            import base64
            base64.b64decode(key_data)
            
            return True

        except Exception:
            return False

    def get_key_fingerprint(self, public_key: str) -> Optional[str]:
        """
        Get fingerprint for a public key.
        
        Args:
            public_key: Public key string
            
        Returns:
            Fingerprint hex string or None if invalid
        """
        try:
            # Parse the public key
            parts = public_key.strip().split()
            if len(parts) < 2:
                return None

            key_type = parts[0]
            key_data = parts[1]

            # Create appropriate key object
            import base64
            key_bytes = base64.b64decode(key_data)
            
            if key_type == 'ssh-rsa':
                key = RSAKey(data=key_bytes)
            elif key_type == 'ssh-dss':
                key = DSSKey(data=key_bytes)
            elif key_type.startswith('ecdsa-'):
                key = ECDSAKey(data=key_bytes)
            elif key_type == 'ssh-ed25519':
                key = Ed25519Key(data=key_bytes)
            else:
                return None

            return key.get_fingerprint().hex()

        except Exception as e:
            logger.error(f"Failed to get key fingerprint: {e}")
            return None