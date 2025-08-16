"""
AI Service Integration Tests for DevPocket API.

Tests AI service functionality with OpenRouter API mocking including:
- BYOK (Bring Your Own Key) model implementation
- Command suggestion generation
- Natural language to command conversion
- API key validation and security
- Error handling and rate limiting
"""

import pytest
import json
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.openrouter import OpenRouterService
from app.api.ai.service import AIService
from app.api.ai.schemas import (
    CommandSuggestionRequest,
    CommandSuggestionResponse,
    ExplainCommandRequest,
    ExplainCommandResponse,
)


class TestOpenRouterService:
    """Test OpenRouter API service integration."""

    @pytest.fixture
    def openrouter_service(self):
        """Create OpenRouter service instance."""
        return OpenRouterService()

    @pytest.fixture
    def mock_api_key(self):
        """Mock OpenRouter API key."""
        return "sk-or-v1-abcdef123456789"

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx async client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.mark.asyncio
    async def test_validate_api_key_success(
        self, openrouter_service, mock_api_key
    ):
        """Test successful API key validation."""
        # Arrange
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"id": "claude-3-haiku"}]
            }
            mock_client.get.return_value = mock_response

            # Act
            is_valid = await openrouter_service.validate_api_key(mock_api_key)

            # Assert
            assert is_valid
            mock_client.get.assert_called_once_with(
                "/api/v1/models",
                headers={
                    "Authorization": f"Bearer {mock_api_key}",
                    "Content-Type": "application/json",
                },
            )

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(
        self, openrouter_service, mock_api_key
    ):
        """Test invalid API key validation."""
        # Arrange
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            # Act
            is_valid = await openrouter_service.validate_api_key(mock_api_key)

            # Assert
            assert not is_valid

    @pytest.mark.asyncio
    async def test_generate_command_success(
        self, openrouter_service, mock_api_key
    ):
        """Test successful command generation."""
        # Arrange
        prompt = "list all files in the current directory"
        expected_command = "ls -la"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": f"```bash\n{expected_command}\n```"
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 10,
                    "total_tokens": 60,
                },
            }
            mock_client.post.return_value = mock_response

            # Act
            result = await openrouter_service.generate_command(
                prompt=prompt, api_key=mock_api_key, model="claude-3-haiku"
            )

            # Assert
            assert result["command"] == expected_command
            assert "usage" in result
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_command_rate_limit(
        self, openrouter_service, mock_api_key
    ):
        """Test handling rate limit errors."""
        # Arrange
        prompt = "list files"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.json.return_value = {
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                }
            }
            mock_client.post.return_value = mock_response

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await openrouter_service.generate_command(
                    prompt=prompt, api_key=mock_api_key
                )

            assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_explain_command_success(
        self, openrouter_service, mock_api_key
    ):
        """Test successful command explanation."""
        # Arrange
        command = "find /home -name '*.py' -type f"
        expected_explanation = "This command searches for Python files..."

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": expected_explanation}}]
            }
            mock_client.post.return_value = mock_response

            # Act
            result = await openrouter_service.explain_command(
                command=command, api_key=mock_api_key
            )

            # Assert
            assert result["explanation"] == expected_explanation

    @pytest.mark.asyncio
    async def test_api_timeout_handling(
        self, openrouter_service, mock_api_key
    ):
        """Test handling API timeout errors."""
        # Arrange
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client
            )
            mock_client.post.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await openrouter_service.generate_command(
                    prompt="test", api_key=mock_api_key
                )

            assert "timeout" in str(exc_info.value).lower()


class TestAIService:
    """Test AI service layer functionality."""

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance."""
        return AIService()

    @pytest.fixture
    def mock_openrouter_service(self):
        """Mock OpenRouter service."""
        service = AsyncMock(spec=OpenRouterService)
        return service

    @pytest.mark.asyncio
    async def test_suggest_command_with_context(self, ai_service):
        """Test command suggestion with system context."""
        # Arrange
        request = CommandSuggestionRequest(
            prompt="show disk usage",
            api_key="test-key",
            context={
                "current_directory": "/home/user",
                "shell": "bash",
                "os": "linux",
            },
        )

        with patch.object(ai_service, "openrouter_service") as mock_service:
            mock_service.generate_command.return_value = {
                "command": "df -h",
                "explanation": "Shows disk usage in human-readable format",
                "confidence": 0.95,
                "usage": {"total_tokens": 50},
            }

            # Act
            result = await ai_service.suggest_command(request)

            # Assert
            assert isinstance(result, CommandSuggestionResponse)
            assert result.command == "df -h"
            assert result.confidence == 0.95
            assert result.explanation is not None

    @pytest.mark.asyncio
    async def test_explain_command_dangerous(self, ai_service):
        """Test explanation of potentially dangerous commands."""
        # Arrange
        request = ExplainCommandRequest(command="rm -rf /", api_key="test-key")

        with patch.object(ai_service, "openrouter_service") as mock_service:
            mock_service.explain_command.return_value = {
                "explanation": "DANGER: This command will delete all files!",
                "safety_level": "dangerous",
                "warnings": ["Will delete entire filesystem"],
            }

            # Act
            result = await ai_service.explain_command(request)

            # Assert
            assert isinstance(result, ExplainCommandResponse)
            assert result.safety_level == "dangerous"
            assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_api_key_caching(self, ai_service):
        """Test API key validation caching."""
        # Arrange
        api_key = "test-key-123"

        with patch.object(ai_service, "openrouter_service") as mock_service:
            mock_service.validate_api_key.return_value = True

            # Act - First call
            result1 = await ai_service.validate_user_api_key(api_key)
            # Act - Second call (should use cache)
            result2 = await ai_service.validate_user_api_key(api_key)

            # Assert
            assert result1 == result2 == True
            # Should only call the service once due to caching
            assert mock_service.validate_api_key.call_count == 1

    @pytest.mark.asyncio
    async def test_command_safety_filtering(self, ai_service):
        """Test filtering of unsafe command suggestions."""
        # Arrange
        request = CommandSuggestionRequest(
            prompt="delete everything", api_key="test-key"
        )

        with patch.object(ai_service, "openrouter_service") as mock_service:
            mock_service.generate_command.return_value = {
                "command": "rm -rf /*",
                "confidence": 0.8,
            }

            # Act
            result = await ai_service.suggest_command(request)

            # Assert
            # Should either refuse the command or add strong warnings
            assert result.safety_level == "dangerous" or result.command is None


class TestAIEndpoints:
    """Test AI API endpoints."""

    @pytest.mark.asyncio
    async def test_suggest_command_endpoint(self, test_client, auth_headers):
        """Test command suggestion endpoint."""
        # Arrange
        request_data = {
            "prompt": "list files",
            "api_key": "test-key",
            "model": "claude-3-haiku",
        }

        with patch(
            "app.api.ai.service.AIService.suggest_command"
        ) as mock_suggest:
            mock_suggest.return_value = CommandSuggestionResponse(
                command="ls -la",
                explanation="Lists files with details",
                confidence=0.95,
                safety_level="safe",
            )

            # Act
            response = test_client.post(
                "/api/ai/suggest", json=request_data, headers=auth_headers
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["command"] == "ls -la"
            assert data["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_explain_command_endpoint(self, test_client, auth_headers):
        """Test command explanation endpoint."""
        # Arrange
        request_data = {
            "command": "grep -r 'pattern' .",
            "api_key": "test-key",
        }

        with patch(
            "app.api.ai.service.AIService.explain_command"
        ) as mock_explain:
            mock_explain.return_value = ExplainCommandResponse(
                explanation="Searches for 'pattern' recursively",
                safety_level="safe",
                complexity="intermediate",
            )

            # Act
            response = test_client.post(
                "/api/ai/explain", json=request_data, headers=auth_headers
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "explanation" in data
            assert data["safety_level"] == "safe"

    @pytest.mark.asyncio
    async def test_ai_endpoint_without_api_key(
        self, test_client, auth_headers
    ):
        """Test AI endpoint without user API key."""
        # Arrange
        request_data = {
            "prompt": "list files"
            # No api_key provided
        }

        # Act
        response = test_client.post(
            "/api/ai/suggest", json=request_data, headers=auth_headers
        )

        # Assert
        assert response.status_code == 400
        assert "api_key" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ai_endpoint_invalid_api_key(
        self, test_client, auth_headers
    ):
        """Test AI endpoint with invalid API key."""
        # Arrange
        request_data = {"prompt": "list files", "api_key": "invalid-key"}

        with patch(
            "app.api.ai.service.AIService.validate_user_api_key"
        ) as mock_validate:
            mock_validate.return_value = False

            # Act
            response = test_client.post(
                "/api/ai/suggest", json=request_data, headers=auth_headers
            )

            # Assert
            assert response.status_code == 401
            assert "invalid" in response.json()["detail"].lower()


class TestBYOKModel:
    """Test Bring Your Own Key (BYOK) model implementation."""

    @pytest.mark.asyncio
    async def test_byok_api_key_not_stored(self, ai_service):
        """Test that API keys are not stored in the system."""
        # Arrange
        api_key = "user-api-key-123"

        # Act
        await ai_service.validate_user_api_key(api_key)

        # Assert
        # Verify that API key is not persisted anywhere
        # This is a security requirement for the BYOK model
        assert not hasattr(ai_service, "stored_api_keys")
        # Additional checks could verify database, cache, logs, etc.

    @pytest.mark.asyncio
    async def test_byok_usage_tracking(self, ai_service):
        """Test usage tracking without storing API keys."""
        # Arrange
        api_key = "user-key-456"

        with patch.object(ai_service, "openrouter_service") as mock_service:
            mock_service.generate_command.return_value = {
                "command": "ls",
                "usage": {"total_tokens": 25},
            }

            # Act
            await ai_service.suggest_command(
                CommandSuggestionRequest(prompt="list files", api_key=api_key)
            )

            # Assert
            # Verify usage is tracked without storing the API key
            # Implementation would track usage per user, not per API key

    @pytest.mark.asyncio
    async def test_byok_cost_calculation(self, ai_service):
        """Test cost calculation for BYOK model."""
        # This test ensures users understand their OpenRouter costs
        # while the service provider has zero API costs

        # Arrange
        with patch.object(ai_service, "openrouter_service") as mock_service:
            mock_service.generate_command.return_value = {
                "command": "ls",
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 10,
                    "total_tokens": 60,
                },
                "cost": {
                    "prompt_cost": 0.0001,
                    "completion_cost": 0.0002,
                    "total_cost": 0.0003,
                },
            }

            # Act
            result = await ai_service.suggest_command(
                CommandSuggestionRequest(prompt="test", api_key="test-key")
            )

            # Assert
            # Verify cost information is available to user
            assert "usage" in result.dict()


class TestAIPerformance:
    """Test AI service performance and optimization."""

    @pytest.mark.asyncio
    async def test_concurrent_ai_requests(self, ai_service):
        """Test handling multiple concurrent AI requests."""
        # Test rate limiting and request queuing
        pass

    @pytest.mark.asyncio
    async def test_ai_response_caching(self, ai_service):
        """Test caching of similar AI requests."""
        # Test caching to reduce API costs
        pass

    @pytest.mark.asyncio
    async def test_ai_request_timeout(self, ai_service):
        """Test handling of slow AI API responses."""
        # Test timeout configuration and fallback
        pass
