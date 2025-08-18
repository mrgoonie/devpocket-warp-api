"""
Comprehensive tests for OpenRouter service.

Tests all OpenRouter API integration methods including:
- API key validation
- Command suggestions
- Command explanations  
- Error analysis
- Command optimization
- Model listing
- Usage statistics
- Rate limiting
- Error handling
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.openrouter import AIResponse, OpenRouterService


@pytest.mark.services
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
    def mock_completion_response(self):
        """Mock successful completion response."""
        return {
            "choices": [
                {
                    "message": {"content": "Test AI response"},
                    "finish_reason": "stop"
                }
            ],
            "model": "gpt-3.5-turbo",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 10,
                "total_tokens": 60,
            },
        }

    # API Key Validation Tests
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, openrouter_service, mock_api_key):
        """Test successful API key validation with account info."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock models response
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {
                "data": [
                    {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                    {"id": "gpt-4", "name": "GPT-4"}
                ]
            }
            
            # Mock auth/key response
            auth_response = MagicMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {
                "data": {
                    "label": "Test API Key",
                    "usage": 1000,
                    "limit": 10000,
                    "is_free_tier": False
                }
            }
            
            mock_client.get.side_effect = [models_response, auth_response]

            result = await openrouter_service.validate_api_key(mock_api_key)

            assert result["valid"] is True
            assert result["models_available"] == 2
            assert result["account_info"]["label"] == "Test API Key"
            assert result["account_info"]["usage"] == 1000
            assert result["account_info"]["limit"] == 10000
            assert result["account_info"]["is_free_tier"] is False
            assert "timestamp" in result
            assert "recommended_models" in result

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, openrouter_service, mock_api_key):
        """Test invalid API key validation."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_client.get.return_value = mock_response

            result = await openrouter_service.validate_api_key(mock_api_key)

            assert result["valid"] is False
            assert "error" in result
            assert "401" in result["error"]
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_validate_api_key_timeout(self, openrouter_service, mock_api_key):
        """Test API key validation timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await openrouter_service.validate_api_key(mock_api_key)

            assert result["valid"] is False
            assert "timeout" in result["error"].lower()

    # Command Suggestion Tests
    @pytest.mark.asyncio
    async def test_suggest_command_success(self, openrouter_service, mock_api_key, mock_completion_response):
        """Test successful command suggestion."""
        description = "list all files in the current directory"
        context = {"working_directory": "/home/user", "operating_system": "linux"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_completion_response
            mock_client.post.return_value = mock_response

            result = await openrouter_service.suggest_command(
                api_key=mock_api_key,
                description=description,
                context=context
            )

            assert isinstance(result, AIResponse)
            assert result.content == "Test AI response"
            assert result.model == "gpt-3.5-turbo"
            assert result.usage["total_tokens"] == 60
            assert result.finish_reason == "stop"
            assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_suggest_command_rate_limit_exceeded(self, openrouter_service, mock_api_key):
        """Test rate limit handling in command suggestion."""
        # Fill up the rate limit
        for _ in range(51):  # Exceed the 50 request limit
            openrouter_service._rate_limits[mock_api_key] = [datetime.now(UTC)] * 51

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await openrouter_service.suggest_command(
                api_key=mock_api_key,
                description="test command"
            )

    # Command Explanation Tests
    @pytest.mark.asyncio
    async def test_explain_command_success(self, openrouter_service, mock_api_key, mock_completion_response):
        """Test successful command explanation."""
        command = "find /home -name '*.py' -type f"
        context = {"user_level": "beginner"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_completion_response
            mock_client.post.return_value = mock_response

            result = await openrouter_service.explain_command(
                api_key=mock_api_key,
                command=command,
                context=context
            )

            assert isinstance(result, AIResponse)
            assert result.content == "Test AI response"

    # Error Analysis Tests
    @pytest.mark.asyncio
    async def test_explain_error_success(self, openrouter_service, mock_api_key, mock_completion_response):
        """Test successful error explanation."""
        command = "ls /nonexistent"
        error_output = "ls: cannot access '/nonexistent': No such file or directory"
        exit_code = 2
        context = {"working_directory": "/home/user"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_completion_response
            mock_client.post.return_value = mock_response

            result = await openrouter_service.explain_error(
                api_key=mock_api_key,
                command=command,
                error_output=error_output,
                exit_code=exit_code,
                context=context
            )

            assert isinstance(result, AIResponse)
            assert result.content == "Test AI response"

    # Command Optimization Tests
    @pytest.mark.asyncio
    async def test_optimize_command_success(self, openrouter_service, mock_api_key, mock_completion_response):
        """Test successful command optimization."""
        command = "find . -name '*.txt' | xargs grep 'pattern'"
        context = {"performance_issues": "slow execution", "frequency": "daily"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_completion_response
            mock_client.post.return_value = mock_response

            result = await openrouter_service.optimize_command(
                api_key=mock_api_key,
                command=command,
                context=context
            )

            assert isinstance(result, AIResponse)
            assert result.content == "Test AI response"

    # Model Management Tests
    @pytest.mark.asyncio
    async def test_get_available_models_success(self, openrouter_service, mock_api_key):
        """Test getting available models."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "id": "gpt-3.5-turbo",
                        "name": "GPT-3.5 Turbo",
                        "description": "Fast and efficient model",
                        "pricing": {"prompt": "0.0015", "completion": "0.002"},
                        "context_length": 4096,
                        "architecture": {"tokenizer": "cl100k_base"},
                        "top_provider": {"context_length": 4096}
                    }
                ]
            }
            mock_client.get.return_value = mock_response

            result = await openrouter_service.get_available_models(mock_api_key)

            assert len(result) == 1
            assert result[0]["id"] == "gpt-3.5-turbo"
            assert result[0]["name"] == "GPT-3.5 Turbo"
            assert result[0]["pricing"]["prompt"] == "0.0015"
            assert result[0]["context_length"] == 4096

    @pytest.mark.asyncio
    async def test_get_available_models_failure(self, openrouter_service, mock_api_key):
        """Test failure when getting available models."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response

            with pytest.raises(Exception, match="Failed to fetch models"):
                await openrouter_service.get_available_models(mock_api_key)

    # Usage Statistics Tests
    @pytest.mark.asyncio
    async def test_get_usage_stats_success(self, openrouter_service, mock_api_key):
        """Test getting usage statistics."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "usage": 5000,
                    "limit": 10000,
                    "is_free_tier": True,
                    "label": "Test Key"
                }
            }
            mock_client.get.return_value = mock_response

            result = await openrouter_service.get_usage_stats(mock_api_key)

            assert result["usage"] == 5000
            assert result["limit"] == 10000
            assert result["is_free_tier"] is True
            assert result["label"] == "Test Key"
            assert "rate_limit" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_usage_stats_failure(self, openrouter_service, mock_api_key):
        """Test failure when getting usage statistics."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            with pytest.raises(Exception, match="Failed to fetch usage stats"):
                await openrouter_service.get_usage_stats(mock_api_key)

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_completion_request_timeout(self, openrouter_service, mock_api_key):
        """Test timeout handling in completion requests."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(Exception, match="Request timeout"):
                await openrouter_service.suggest_command(
                    api_key=mock_api_key,
                    description="test"
                )

    @pytest.mark.asyncio
    async def test_completion_request_api_error(self, openrouter_service, mock_api_key):
        """Test API error handling in completion requests."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": {"message": "Internal server error"}}
            mock_response.content = b'{"error": {"message": "Internal server error"}}'
            mock_client.post.return_value = mock_response

            with pytest.raises(Exception, match="OpenRouter API error"):
                await openrouter_service.suggest_command(
                    api_key=mock_api_key,
                    description="test"
                )

    # Rate Limiting Tests
    @pytest.mark.asyncio
    async def test_rate_limit_check_passes(self, openrouter_service, mock_api_key):
        """Test rate limit check passes for new API key."""
        result = await openrouter_service._check_rate_limit(mock_api_key)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_check_fails(self, openrouter_service, mock_api_key):
        """Test rate limit check fails when limit exceeded."""
        # Fill the rate limit
        openrouter_service._rate_limits[mock_api_key] = [datetime.now(UTC)] * 50
        
        result = await openrouter_service._check_rate_limit(mock_api_key)
        assert result is False

    @pytest.mark.asyncio
    async def test_rate_limit_cleanup(self, openrouter_service, mock_api_key):
        """Test rate limit cleanup of old requests."""
        from datetime import timedelta
        
        # Add old requests that should be cleaned up
        old_time = datetime.now(UTC) - timedelta(seconds=120)
        openrouter_service._rate_limits[mock_api_key] = [old_time] * 10
        
        result = await openrouter_service._check_rate_limit(mock_api_key)
        assert result is True
        assert len(openrouter_service._rate_limits[mock_api_key]) == 1  # Only the new request

    # Private Method Tests
    def test_prompt_generation_methods(self, openrouter_service):
        """Test prompt generation helper methods."""
        # Test system prompts
        cmd_prompt = openrouter_service._get_command_suggestion_prompt()
        assert "command-line assistant" in cmd_prompt
        assert "JSON" in cmd_prompt

        explain_prompt = openrouter_service._get_command_explanation_prompt()
        assert "command-line instructor" in explain_prompt

        error_prompt = openrouter_service._get_error_analysis_prompt()
        assert "debugging expert" in error_prompt

        opt_prompt = openrouter_service._get_optimization_prompt()
        assert "performance optimization" in opt_prompt

    def test_user_prompt_building(self, openrouter_service):
        """Test user prompt building methods."""
        # Test command request prompt
        context = {
            "working_directory": "/home/user",
            "previous_commands": ["ls", "cd project", "git status"],
            "operating_system": "linux"
        }
        prompt = openrouter_service._build_command_request_prompt("list files", context)
        assert "list files" in prompt
        assert "/home/user" in prompt
        assert "git status" in prompt
        assert "linux" in prompt

        # Test command explanation prompt
        context = {"working_directory": "/home", "user_level": "beginner"}
        prompt = openrouter_service._build_command_explanation_prompt("ls -la", context)
        assert "ls -la" in prompt
        assert "/home" in prompt
        assert "beginner" in prompt

        # Test error analysis prompt
        context = {"working_directory": "/tmp", "environment": {"SHELL": "/bin/bash"}}
        prompt = openrouter_service._build_error_analysis_prompt(
            "rm file.txt", "No such file", 1, context
        )
        assert "rm file.txt" in prompt
        assert "No such file" in prompt
        assert "Exit code: 1" in prompt
        assert "/tmp" in prompt

        # Test optimization prompt
        context = {"performance_issues": "slow", "frequency": "daily"}
        prompt = openrouter_service._build_optimization_prompt("find . -name '*.txt'", context)
        assert "find . -name '*.txt'" in prompt
        assert "slow" in prompt
        assert "daily" in prompt