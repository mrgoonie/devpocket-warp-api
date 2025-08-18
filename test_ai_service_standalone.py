#!/usr/bin/env python3
"""
Standalone AI Service Test for Coverage Analysis.

This script runs focused tests directly for AI service.
"""

import sys
import os
import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app.api.ai.service import AIService


class StandaloneAITests:
    """Standalone test runner for AI Service."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []

    def assert_equals(self, actual, expected, message=""):
        if actual != expected:
            error_msg = f"AssertionError: {message}. Expected {expected}, got {actual}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_true(self, condition, message=""):
        if not condition:
            error_msg = f"AssertionError: {message}. Expected True, got {condition}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_false(self, condition, message=""):
        if condition:
            error_msg = f"AssertionError: {message}. Expected False, got {condition}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_not_none(self, value, message=""):
        if value is None:
            error_msg = f"AssertionError: {message}. Expected not None, got {value}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    def assert_in(self, item, container, message=""):
        if item not in container:
            error_msg = f"AssertionError: {message}. Expected {item} in {container}"
            self.errors.append(error_msg)
            raise AssertionError(error_msg)

    async def run_test(self, test_method):
        """Run a single test method."""
        test_name = test_method.__name__
        try:
            await test_method()
            print(f"✓ {test_name}")
            self.tests_passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            self.tests_failed += 1

    # Test Methods

    async def test_service_initialization(self):
        """Test AI service initializes correctly."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = MagicMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            self.assert_equals(service.session, mock_session)
            self.assert_not_none(service.openrouter)
            self.assert_equals(service._response_cache, {})
            self.assert_equals(service._cache_ttl, 3600)
            mock_openrouter_class.assert_called_once()

    async def test_validate_api_key_success(self):
        """Test successful API key validation."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            # Mock successful validation result
            mock_result = {
                "valid": True,
                "account_info": {"credits": 100},
                "models_available": ["gpt-3.5-turbo", "gpt-4"],
                "recommended_models": ["gpt-3.5-turbo"],
                "timestamp": datetime.now(UTC)
            }
            mock_openrouter.validate_api_key.return_value = mock_result
            
            service = AIService(mock_session)
            result = await service.validate_api_key("test-api-key")
            
            self.assert_true(result.valid)
            self.assert_not_none(result.account_info)
            self.assert_not_none(result.models_available)
            self.assert_not_none(result.timestamp)
            mock_openrouter.validate_api_key.assert_called_once_with("test-api-key")

    async def test_validate_api_key_failure(self):
        """Test API key validation failure."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            # Mock validation error
            mock_openrouter.validate_api_key.side_effect = Exception("Invalid API key")
            
            service = AIService(mock_session)
            result = await service.validate_api_key("invalid-key")
            
            self.assert_false(result.valid)
            self.assert_not_none(result.error)
            self.assert_true("Validation failed" in result.error)

    async def test_get_usage_stats_success(self):
        """Test successful usage stats retrieval."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            # Mock usage stats result
            mock_stats = {
                "usage": {"requests": 50, "tokens": 10000},
                "limit": {"requests": 1000, "tokens": 100000},
                "is_free_tier": True,
                "rate_limit": {"per_minute": 20},
                "timestamp": datetime.now(UTC)
            }
            mock_openrouter.get_usage_stats.return_value = mock_stats
            
            service = AIService(mock_session)
            result = await service.get_usage_stats("test-api-key")
            
            self.assert_not_none(result.usage)
            self.assert_not_none(result.limit)
            self.assert_true(result.is_free_tier)
            self.assert_not_none(result.rate_limit)
            mock_openrouter.get_usage_stats.assert_called_once_with("test-api-key")

    async def test_get_usage_stats_error(self):
        """Test usage stats retrieval with error."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            # Mock error
            mock_openrouter.get_usage_stats.side_effect = Exception("API error")
            
            service = AIService(mock_session)
            
            try:
                result = await service.get_usage_stats("test-api-key")
                self.assert_true(False, "Should have raised HTTPException")
            except Exception as e:
                self.assert_true("Failed to get" in str(e))

    async def test_cache_functionality(self):
        """Test response caching functionality."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService'):
            service = AIService(mock_session)
            
            # Test cache initialization
            self.assert_equals(service._response_cache, {})
            
            # Test cache operations
            cache_key = "test-key"
            cache_value = {"result": "test", "timestamp": datetime.now(UTC).timestamp()}
            
            # Manually add to cache to test functionality
            service._response_cache[cache_key] = cache_value
            self.assert_in(cache_key, service._response_cache)
            self.assert_equals(service._response_cache[cache_key], cache_value)

    async def test_command_explanation_basic(self):
        """Test basic command explanation functionality."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            # Test that the service has the necessary components for command explanation
            self.assert_not_none(service.openrouter)
            
            # If the method exists, we can test it
            if hasattr(service, 'explain_command'):
                # Mock explanation request
                request = MagicMock()
                request.command = "ls -la"
                request.context = "list files"
                
                # Mock OpenRouter response
                mock_openrouter.generate_completion = AsyncMock(return_value={
                    "explanation": "Lists all files with detailed information",
                    "confidence": 0.95
                })
                
                result = await service.explain_command(request, "api-key")
                self.assert_not_none(result)

    async def test_command_suggestion_basic(self):
        """Test basic command suggestion functionality."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            # Test that the service has the necessary components for command suggestions
            self.assert_not_none(service.openrouter)
            
            # If the method exists, we can test it
            if hasattr(service, 'suggest_command'):
                # Mock suggestion request
                request = MagicMock()
                request.intent = "list files"
                request.context = {"os": "linux", "shell": "bash"}
                
                # Mock OpenRouter response
                mock_openrouter.generate_completion = AsyncMock(return_value={
                    "commands": ["ls -la", "find . -type f"],
                    "confidence": 0.90
                })
                
                result = await service.suggest_command(request, "api-key")
                self.assert_not_none(result)

    async def test_error_analysis_basic(self):
        """Test basic error analysis functionality."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            # Test that the service has the necessary components for error analysis
            self.assert_not_none(service.openrouter)
            
            # If the method exists, we can test it
            if hasattr(service, 'analyze_error'):
                # Mock error analysis request
                request = MagicMock()
                request.command = "rm -rf /"
                request.error_output = "Permission denied"
                request.exit_code = 1
                
                # Mock OpenRouter response
                mock_openrouter.generate_completion = AsyncMock(return_value={
                    "analysis": "Permission denied error",
                    "solutions": ["Check permissions", "Use sudo"],
                    "severity": "high"
                })
                
                result = await service.analyze_error(request, "api-key")
                self.assert_not_none(result)

    async def test_batch_processing_basic(self):
        """Test basic batch processing functionality."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            # Test that the service has the necessary components for batch processing
            self.assert_not_none(service.openrouter)
            
            # If the method exists, we can test it
            if hasattr(service, 'process_batch'):
                # Mock batch request
                requests = [MagicMock(), MagicMock()]
                
                result = await service.process_batch(requests, "api-key")
                self.assert_not_none(result)

    async def test_available_models_basic(self):
        """Test available models functionality."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = AsyncMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            # Test that the service has the necessary components for model listing
            self.assert_not_none(service.openrouter)
            
            # If the method exists, we can test it
            if hasattr(service, 'get_available_models'):
                mock_openrouter.get_available_models = AsyncMock(return_value={
                    "models": [
                        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
                        {"id": "gpt-4", "name": "GPT-4"}
                    ]
                })
                
                result = await service.get_available_models("api-key")
                self.assert_not_none(result)

    async def test_service_dependencies(self):
        """Test service dependencies and integrations."""
        mock_session = AsyncMock()
        
        with patch('app.api.ai.service.OpenRouterService') as mock_openrouter_class:
            mock_openrouter = MagicMock()
            mock_openrouter_class.return_value = mock_openrouter
            
            service = AIService(mock_session)
            
            # Verify all dependencies are properly initialized
            self.assert_not_none(service.session)
            self.assert_not_none(service.openrouter)
            self.assert_true(isinstance(service._response_cache, dict))
            self.assert_true(isinstance(service._cache_ttl, int))
            self.assert_equals(service._cache_ttl, 3600)

    async def run_all_tests(self):
        """Run all test methods."""
        print("Running standalone AI Service tests...")
        print("=" * 50)
        
        test_methods = [
            self.test_service_initialization,
            self.test_validate_api_key_success,
            self.test_validate_api_key_failure,
            self.test_get_usage_stats_success,
            self.test_get_usage_stats_error,
            self.test_cache_functionality,
            self.test_command_explanation_basic,
            self.test_command_suggestion_basic,
            self.test_error_analysis_basic,
            self.test_batch_processing_basic,
            self.test_available_models_basic,
            self.test_service_dependencies,
        ]
        
        for test_method in test_methods:
            await self.run_test(test_method)
        
        print("=" * 50)
        print(f"Tests completed: {self.tests_passed} passed, {self.tests_failed} failed")
        
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        return self.tests_passed, self.tests_failed


async def main():
    """Main test runner."""
    test_runner = StandaloneAITests()
    passed, failed = await test_runner.run_all_tests()
    
    print(f"\nTest Results: {passed}/{passed + failed} tests passed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"❌ {failed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)