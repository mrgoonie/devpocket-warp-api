"""
OpenRouter integration service for DevPocket AI features.

Provides BYOK (Bring Your Own Key) integration with OpenRouter API
for AI-powered command suggestions, explanations, and error analysis.
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import httpx
from dataclasses import dataclass

from app.core.logging import logger
from app.core.config import settings


@dataclass
class AIResponse:
    """AI response data structure."""

    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    response_time_ms: int
    timestamp: datetime


@dataclass
class AIError:
    """AI error data structure."""

    error_type: str
    message: str
    code: Optional[int]
    details: Optional[Dict[str, Any]]
    timestamp: datetime


class OpenRouterService:
    """Service for OpenRouter API integration."""

    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = 30.0
        self.max_retries = 2

        # Default models for different use cases
        self.models = {
            "command_suggestion": "google/gemini-2.5-flash",
            "command_explanation": "google/gemini-2.5-flash",
            "error_analysis": "google/gemini-2.5-flash",
            "optimization": "google/gemini-2.5-flash",
            "general": "google/gemini-2.5-flash",
        }

        # Rate limiting (simple in-memory store)
        self._rate_limits: Dict[str, List[datetime]] = {}
        self._rate_limit_window = 60  # seconds
        self._rate_limit_requests = 50  # requests per window

    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate OpenRouter API key and get account information.

        Args:
            api_key: OpenRouter API key

        Returns:
            Dict containing validation result and account info
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": f"{settings.app_name} - Key Validation",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test with a simple models list request
                response = await client.get(f"{self.base_url}/models", headers=headers)

                if response.status_code == 200:
                    models_data = response.json()

                    # Get account info
                    try:
                        auth_response = await client.get(
                            f"{self.base_url}/auth/key", headers=headers
                        )

                        account_info = {}
                        if auth_response.status_code == 200:
                            account_data = auth_response.json()
                            account_info = {
                                "label": account_data.get("data", {}).get(
                                    "label", "Unknown"
                                ),
                                "usage": account_data.get("data", {}).get("usage", 0),
                                "limit": account_data.get("data", {}).get("limit"),
                                "is_free_tier": account_data.get("data", {}).get(
                                    "is_free_tier", True
                                ),
                            }
                    except Exception:
                        account_info = {"label": "Unknown", "usage": 0}

                    return {
                        "valid": True,
                        "models_available": len(models_data.get("data", [])),
                        "account_info": account_info,
                        "recommended_models": list(self.models.values()),
                        "timestamp": datetime.now(timezone.utc),
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"API key validation failed: {response.status_code}",
                        "details": response.text[:200],
                        "timestamp": datetime.now(timezone.utc),
                    }

        except httpx.TimeoutException:
            return {
                "valid": False,
                "error": "Request timeout - OpenRouter API is unreachable",
                "timestamp": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error(f"OpenRouter API key validation error: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "timestamp": datetime.now(timezone.utc),
            }

    async def suggest_command(
        self,
        api_key: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """
        Get command suggestions based on natural language description.

        Args:
            api_key: User's OpenRouter API key
            description: Natural language description of desired command
            context: Additional context (working directory, previous commands, etc.)
            model: Specific model to use (optional)

        Returns:
            AIResponse with command suggestions
        """
        if not await self._check_rate_limit(api_key):
            raise Exception("Rate limit exceeded for API key")

        model = model or self.models["command_suggestion"]

        # Build context-aware prompt
        system_prompt = self._get_command_suggestion_prompt()
        user_prompt = self._build_command_request_prompt(description, context)

        return await self._make_completion_request(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            use_case="command_suggestion",
        )

    async def explain_command(
        self,
        api_key: str,
        command: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """
        Get detailed explanation of a command.

        Args:
            api_key: User's OpenRouter API key
            command: Command to explain
            context: Additional context
            model: Specific model to use (optional)

        Returns:
            AIResponse with command explanation
        """
        if not await self._check_rate_limit(api_key):
            raise Exception("Rate limit exceeded for API key")

        model = model or self.models["command_explanation"]

        system_prompt = self._get_command_explanation_prompt()
        user_prompt = self._build_command_explanation_prompt(command, context)

        return await self._make_completion_request(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            use_case="command_explanation",
        )

    async def explain_error(
        self,
        api_key: str,
        command: str,
        error_output: str,
        exit_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """
        Analyze and explain command errors.

        Args:
            api_key: User's OpenRouter API key
            command: Command that failed
            error_output: Error output from command
            exit_code: Command exit code
            context: Additional context
            model: Specific model to use (optional)

        Returns:
            AIResponse with error analysis and suggestions
        """
        if not await self._check_rate_limit(api_key):
            raise Exception("Rate limit exceeded for API key")

        model = model or self.models["error_analysis"]

        system_prompt = self._get_error_analysis_prompt()
        user_prompt = self._build_error_analysis_prompt(
            command, error_output, exit_code, context
        )

        return await self._make_completion_request(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            use_case="error_analysis",
        )

    async def optimize_command(
        self,
        api_key: str,
        command: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """
        Get optimization suggestions for a command.

        Args:
            api_key: User's OpenRouter API key
            command: Command to optimize
            context: Additional context
            model: Specific model to use (optional)

        Returns:
            AIResponse with optimization suggestions
        """
        if not await self._check_rate_limit(api_key):
            raise Exception("Rate limit exceeded for API key")

        model = model or self.models["optimization"]

        system_prompt = self._get_optimization_prompt()
        user_prompt = self._build_optimization_prompt(command, context)

        return await self._make_completion_request(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            use_case="optimization",
        )

    async def get_available_models(self, api_key: str) -> List[Dict[str, Any]]:
        """
        Get list of available models for the API key.

        Args:
            api_key: User's OpenRouter API key

        Returns:
            List of available models with metadata
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)

                if response.status_code == 200:
                    models_data = response.json()

                    # Filter and format models
                    available_models = []
                    for model in models_data.get("data", []):
                        available_models.append(
                            {
                                "id": model.get("id"),
                                "name": model.get("name", model.get("id")),
                                "description": model.get("description", ""),
                                "pricing": {
                                    "prompt": model.get("pricing", {}).get(
                                        "prompt", "0"
                                    ),
                                    "completion": model.get("pricing", {}).get(
                                        "completion", "0"
                                    ),
                                },
                                "context_length": model.get("context_length", 0),
                                "architecture": model.get("architecture", {}),
                                "top_provider": model.get("top_provider", {}),
                            }
                        )

                    return available_models
                else:
                    raise Exception(f"Failed to fetch models: {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            raise

    async def get_usage_stats(self, api_key: str) -> Dict[str, Any]:
        """
        Get usage statistics for the API key.

        Args:
            api_key: User's OpenRouter API key

        Returns:
            Usage statistics
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/auth/key", headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    key_data = data.get("data", {})

                    return {
                        "usage": key_data.get("usage", 0),
                        "limit": key_data.get("limit"),
                        "is_free_tier": key_data.get("is_free_tier", True),
                        "label": key_data.get("label", ""),
                        "rate_limit": {
                            "requests_per_minute": 50,  # Default limit
                            "tokens_per_minute": None,
                        },
                        "timestamp": datetime.now(timezone.utc),
                    }
                else:
                    raise Exception(
                        f"Failed to fetch usage stats: {response.status_code}"
                    )

        except Exception as e:
            logger.error(f"Error fetching usage stats: {e}")
            raise

    # Private helper methods

    async def _make_completion_request(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        use_case: str,
    ) -> AIResponse:
        """Make completion request to OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": f"https://{settings.app_name.lower().replace(' ', '-')}.app",
            "X-Title": f"{settings.app_name} - {use_case.replace('_', ' ').title()}",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
        }

        start_time = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                response_time_ms = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )

                if response.status_code == 200:
                    data = response.json()
                    choice = data["choices"][0]

                    return AIResponse(
                        content=choice["message"]["content"],
                        model=data.get("model", model),
                        usage=data.get("usage", {}),
                        finish_reason=choice.get("finish_reason", "unknown"),
                        response_time_ms=response_time_ms,
                        timestamp=datetime.now(timezone.utc),
                    )
                else:
                    error_data = response.json() if response.content else {}
                    raise Exception(
                        f"OpenRouter API error: {response.status_code} - {error_data}"
                    )

        except httpx.TimeoutException:
            raise Exception(
                "Request timeout - OpenRouter API is taking too long to respond"
            )
        except Exception as e:
            logger.error(f"OpenRouter completion request error: {e}")
            raise

    async def _check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limits."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self._rate_limit_window)

        if api_key not in self._rate_limits:
            self._rate_limits[api_key] = []

        # Clean old requests
        self._rate_limits[api_key] = [
            req_time
            for req_time in self._rate_limits[api_key]
            if req_time > window_start
        ]

        # Check limit
        if len(self._rate_limits[api_key]) >= self._rate_limit_requests:
            return False

        # Record this request
        self._rate_limits[api_key].append(now)
        return True

    def _get_command_suggestion_prompt(self) -> str:
        """Get system prompt for command suggestions."""
        return """You are a helpful command-line assistant that suggests appropriate shell commands based on natural language descriptions.

Guidelines:
- Provide concise, practical command suggestions
- Include brief explanations of what the commands do
- Suggest safer alternatives when possible
- Consider common Unix/Linux environments
- Format response as JSON with "commands" array containing objects with "command" and "description" fields
- Limit to maximum 5 suggestions
- Prioritize commonly used and safe commands"""

    def _get_command_explanation_prompt(self) -> str:
        """Get system prompt for command explanations."""
        return """You are an expert command-line instructor that provides clear, detailed explanations of shell commands.

Guidelines:
- Break down complex commands into components
- Explain each part and its purpose
- Mention any potential risks or side effects
- Include practical examples when helpful
- Use beginner-friendly language
- Format response as structured text with clear sections"""

    def _get_error_analysis_prompt(self) -> str:
        """Get system prompt for error analysis."""
        return """You are a debugging expert that analyzes command errors and provides solutions.

Guidelines:
- Identify the root cause of the error
- Explain why the error occurred
- Provide specific solutions and alternatives
- Include preventive measures
- Suggest better practices when applicable
- Format response with clear problem/solution structure"""

    def _get_optimization_prompt(self) -> str:
        """Get system prompt for command optimization."""
        return """You are a performance optimization expert for command-line operations.

Guidelines:
- Analyze the command for efficiency improvements
- Suggest more efficient alternatives
- Consider performance, safety, and portability
- Explain the benefits of suggested optimizations
- Include modern tool alternatives when applicable
- Format response with original vs optimized comparison"""

    def _build_command_request_prompt(
        self, description: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt for command suggestions."""
        prompt = f"Task description: {description}\n\n"

        if context:
            if context.get("working_directory"):
                prompt += f"Current directory: {context['working_directory']}\n"
            if context.get("previous_commands"):
                prompt += (
                    f"Recent commands: {', '.join(context['previous_commands'][-3:])}\n"
                )
            if context.get("operating_system"):
                prompt += f"Operating system: {context['operating_system']}\n"

        prompt += "\nPlease suggest appropriate commands for this task."
        return prompt

    def _build_command_explanation_prompt(
        self, command: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt for command explanations."""
        prompt = f"Command to explain: {command}\n\n"

        if context:
            if context.get("working_directory"):
                prompt += f"Context: Running in {context['working_directory']}\n"
            if context.get("user_level"):
                prompt += f"User experience level: {context['user_level']}\n"

        prompt += "Please provide a detailed explanation of this command."
        return prompt

    def _build_error_analysis_prompt(
        self,
        command: str,
        error_output: str,
        exit_code: Optional[int],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build user prompt for error analysis."""
        prompt = f"Failed command: {command}\n"
        prompt += f"Error output: {error_output}\n"

        if exit_code is not None:
            prompt += f"Exit code: {exit_code}\n"

        if context:
            if context.get("working_directory"):
                prompt += f"Working directory: {context['working_directory']}\n"
            if context.get("environment"):
                prompt += f"Environment: {context.get('environment', {}).get('SHELL', 'Unknown shell')}\n"

        prompt += "\nPlease analyze this error and provide solutions."
        return prompt

    def _build_optimization_prompt(
        self, command: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt for command optimization."""
        prompt = f"Command to optimize: {command}\n\n"

        if context:
            if context.get("performance_issues"):
                prompt += f"Performance concerns: {context['performance_issues']}\n"
            if context.get("frequency"):
                prompt += f"Usage frequency: {context['frequency']}\n"

        prompt += "Please suggest optimizations and improvements for this command."
        return prompt
