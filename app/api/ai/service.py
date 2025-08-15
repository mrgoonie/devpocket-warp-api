"""
AI service layer for DevPocket API.

Contains business logic for AI-powered features using BYOK model with OpenRouter.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.user import User
from app.services.openrouter import OpenRouterService, AIResponse
from .schemas import (
    # API Key schemas
    APIKeyValidationResponse,
    AIUsageStats,
    # Command suggestion schemas
    CommandSuggestionRequest,
    CommandSuggestionResponse,
    CommandSuggestion,
    # Command explanation schemas
    CommandExplanationRequest,
    CommandExplanationResponse,
    CommandExplanation,
    # Error analysis schemas
    ErrorAnalysisRequest,
    ErrorAnalysisResponse,
    ErrorAnalysis,
    # Optimization schemas
    CommandOptimizationRequest,
    CommandOptimizationResponse,
    CommandOptimization,
    # Settings and models
    AISettings,
    AISettingsResponse,
    AIModelInfo,
    AvailableModelsResponse,
    # Batch processing
    BatchAIRequest,
    BatchAIResponse,
    # Enums
    AIServiceType,
    ConfidenceLevel,
)


class AIService:
    """Service class for AI-powered features."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.openrouter = OpenRouterService()

        # Simple in-memory cache for responses (in production, use Redis)
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour

    async def validate_api_key(self, api_key: str) -> APIKeyValidationResponse:
        """Validate OpenRouter API key and return account information."""
        try:
            result = await self.openrouter.validate_api_key(api_key)

            return APIKeyValidationResponse(
                valid=result["valid"],
                account_info=result.get("account_info"),
                models_available=result.get("models_available"),
                recommended_models=result.get("recommended_models"),
                error=result.get("error"),
                timestamp=result["timestamp"],
            )

        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return APIKeyValidationResponse(
                valid=False,
                error=f"Validation failed: {str(e)}",
                timestamp=datetime.utcnow(),
            )

    async def get_usage_stats(self, api_key: str) -> AIUsageStats:
        """Get AI service usage statistics for the API key."""
        try:
            stats = await self.openrouter.get_usage_stats(api_key)

            return AIUsageStats(
                usage=stats["usage"],
                limit=stats["limit"],
                is_free_tier=stats["is_free_tier"],
                rate_limit=stats["rate_limit"],
                timestamp=stats["timestamp"],
            )

        except Exception as e:
            logger.error(f"Error getting AI usage stats: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve AI usage statistics",
            )

    async def suggest_command(
        self, user: User, request: CommandSuggestionRequest
    ) -> CommandSuggestionResponse:
        """Get command suggestions using AI."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(
                "suggest", request.description, request.model
            )
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return CommandSuggestionResponse(**cached_response)

            # Prepare context
            context = {
                "working_directory": request.working_directory,
                "previous_commands": request.previous_commands,
                "operating_system": request.operating_system,
                "shell_type": request.shell_type,
                "user_level": request.user_level,
            }

            # Get AI response
            ai_response = await self.openrouter.suggest_command(
                api_key=request.api_key,
                description=request.description,
                context=context,
                model=request.model.value if request.model else None,
            )

            # Parse AI response
            suggestions = self._parse_command_suggestions(
                ai_response, request.max_suggestions, request.include_explanations
            )

            response = CommandSuggestionResponse(
                suggestions=suggestions,
                query_description=request.description,
                context_used=context,
                model_used=ai_response.model,
                response_time_ms=ai_response.response_time_ms,
                tokens_used=ai_response.usage,
                confidence_score=self._calculate_confidence_score(suggestions),
                timestamp=ai_response.timestamp,
            )

            # Cache the response
            self._cache_response(cache_key, response.model_dump())

            logger.info(f"Command suggestions generated for user {user.username}")
            return response

        except Exception as e:
            logger.error(f"Error generating command suggestions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate command suggestions: {str(e)}",
            )

    async def explain_command(
        self, user: User, request: CommandExplanationRequest
    ) -> CommandExplanationResponse:
        """Get detailed command explanation using AI."""
        try:
            # Check cache
            cache_key = self._generate_cache_key(
                "explain", request.command, request.model
            )
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return CommandExplanationResponse(**cached_response)

            # Prepare context
            context = {
                "working_directory": request.working_directory,
                "user_level": request.user_level,
                "detail_level": request.detail_level,
            }

            # Get AI response
            ai_response = await self.openrouter.explain_command(
                api_key=request.api_key,
                command=request.command,
                context=context,
                model=request.model.value if request.model else None,
            )

            # Parse explanation
            explanation = self._parse_command_explanation(
                ai_response,
                request.command,
                request.include_examples,
                request.include_alternatives,
            )

            response = CommandExplanationResponse(
                explanation=explanation,
                model_used=ai_response.model,
                response_time_ms=ai_response.response_time_ms,
                tokens_used=ai_response.usage,
                confidence_score=self._calculate_explanation_confidence(explanation),
                timestamp=ai_response.timestamp,
            )

            # Cache the response
            self._cache_response(cache_key, response.model_dump())

            logger.info(f"Command explanation generated for user {user.username}")
            return response

        except Exception as e:
            logger.error(f"Error generating command explanation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to explain command: {str(e)}",
            )

    async def analyze_error(
        self, user: User, request: ErrorAnalysisRequest
    ) -> ErrorAnalysisResponse:
        """Analyze command error using AI."""
        try:
            # Check cache
            cache_key = self._generate_cache_key(
                "error", f"{request.command}:{request.error_output}", request.model
            )
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return ErrorAnalysisResponse(**cached_response)

            # Prepare context
            context = {
                "working_directory": request.working_directory,
                "environment": request.environment_info,
                "system_info": request.system_info,
            }

            # Get AI response
            ai_response = await self.openrouter.explain_error(
                api_key=request.api_key,
                command=request.command,
                error_output=request.error_output,
                exit_code=request.exit_code,
                context=context,
                model=request.model.value if request.model else None,
            )

            # Parse error analysis
            analysis = self._parse_error_analysis(
                ai_response,
                request.command,
                request.error_output,
                request.include_solutions,
                request.include_prevention,
            )

            response = ErrorAnalysisResponse(
                analysis=analysis,
                original_command=request.command,
                error_summary=request.error_output[:200] + "..."
                if len(request.error_output) > 200
                else request.error_output,
                model_used=ai_response.model,
                response_time_ms=ai_response.response_time_ms,
                tokens_used=ai_response.usage,
                confidence_score=self._calculate_analysis_confidence(analysis),
                timestamp=ai_response.timestamp,
            )

            # Cache the response
            self._cache_response(cache_key, response.model_dump())

            logger.info(f"Error analysis generated for user {user.username}")
            return response

        except Exception as e:
            logger.error(f"Error analyzing command error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to analyze error: {str(e)}",
            )

    async def optimize_command(
        self, user: User, request: CommandOptimizationRequest
    ) -> CommandOptimizationResponse:
        """Get command optimization suggestions using AI."""
        try:
            # Check cache
            cache_key = self._generate_cache_key(
                "optimize", request.command, request.model
            )
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return CommandOptimizationResponse(**cached_response)

            # Prepare context
            context = {
                "usage_frequency": request.usage_frequency,
                "performance_issues": request.performance_issues,
                "environment": request.environment,
                "constraints": request.constraints,
                "optimize_for": request.optimize_for,
            }

            # Get AI response
            ai_response = await self.openrouter.optimize_command(
                api_key=request.api_key,
                command=request.command,
                context=context,
                model=request.model.value if request.model else None,
            )

            # Parse optimization
            optimization = self._parse_command_optimization(
                ai_response, request.command, request.include_modern_alternatives
            )

            response = CommandOptimizationResponse(
                optimization=optimization,
                model_used=ai_response.model,
                response_time_ms=ai_response.response_time_ms,
                tokens_used=ai_response.usage,
                confidence_score=self._calculate_optimization_confidence(optimization),
                timestamp=ai_response.timestamp,
            )

            # Cache the response
            self._cache_response(cache_key, response.model_dump())

            logger.info(f"Command optimization generated for user {user.username}")
            return response

        except Exception as e:
            logger.error(f"Error optimizing command: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to optimize command: {str(e)}",
            )

    async def get_available_models(self, api_key: str) -> AvailableModelsResponse:
        """Get list of available AI models."""
        try:
            models_data = await self.openrouter.get_available_models(api_key)

            models = []
            for model_data in models_data:
                model = AIModelInfo(
                    id=model_data["id"],
                    name=model_data["name"],
                    description=model_data["description"],
                    context_length=model_data["context_length"],
                    pricing=model_data["pricing"],
                    provider=model_data.get("top_provider", {}).get("name", "Unknown"),
                    architecture=model_data["architecture"],
                    performance_tier=self._classify_model_performance(model_data),
                )
                models.append(model)

            # Sort by performance tier and context length
            models.sort(
                key=lambda x: (x.performance_tier, x.context_length), reverse=True
            )

            recommended_models = ["google/gemini-2.5-flash", "google/gemini-2.5-pro"]

            return AvailableModelsResponse(
                models=models,
                total_models=len(models),
                recommended_models=recommended_models,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch available models",
            )

    async def process_batch_requests(
        self, user: User, request: BatchAIRequest
    ) -> BatchAIResponse:
        """Process multiple AI requests in batch."""
        try:
            results = []
            success_count = 0
            error_count = 0
            total_tokens = 0
            start_time = datetime.utcnow()

            for i, req_data in enumerate(request.requests):
                try:
                    # Process based on service type
                    if request.service_type == AIServiceType.COMMAND_SUGGESTION:
                        result = await self._process_batch_suggestion(
                            request.api_key, req_data
                        )
                    elif request.service_type == AIServiceType.COMMAND_EXPLANATION:
                        result = await self._process_batch_explanation(
                            request.api_key, req_data
                        )
                    elif request.service_type == AIServiceType.ERROR_ANALYSIS:
                        result = await self._process_batch_error_analysis(
                            request.api_key, req_data
                        )
                    else:
                        raise ValueError(
                            f"Unsupported service type: {request.service_type}"
                        )

                    results.append(
                        {
                            "index": i,
                            "status": "success",
                            "result": result,
                            "tokens_used": result.get("tokens_used", {}),
                        }
                    )
                    success_count += 1
                    total_tokens += sum(result.get("tokens_used", {}).values())

                except Exception as e:
                    results.append({"index": i, "status": "error", "error": str(e)})
                    error_count += 1

            total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return BatchAIResponse(
                results=results,
                success_count=success_count,
                error_count=error_count,
                total_tokens_used=total_tokens,
                total_response_time_ms=total_time,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error processing batch AI requests: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process batch requests",
            )

    # Private helper methods

    def _generate_cache_key(
        self, service_type: str, content: str, model: Optional[str]
    ) -> str:
        """Generate cache key for response caching."""
        import hashlib

        key_content = f"{service_type}:{content}:{model or 'default'}"
        return hashlib.md5(key_content.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        if cache_key in self._response_cache:
            cached_data = self._response_cache[cache_key]
            if datetime.utcnow() - cached_data["timestamp"] < timedelta(
                seconds=self._cache_ttl
            ):
                return cached_data["response"]
            else:
                # Remove expired cache
                del self._response_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response_data: Dict[str, Any]) -> None:
        """Cache response data."""
        self._response_cache[cache_key] = {
            "response": response_data,
            "timestamp": datetime.utcnow(),
        }

    def _parse_command_suggestions(
        self, ai_response: AIResponse, max_suggestions: int, include_explanations: bool
    ) -> List[CommandSuggestion]:
        """Parse AI response into command suggestions."""
        suggestions = []

        try:
            # Try to parse JSON response
            if ai_response.content.strip().startswith(
                "{"
            ) or ai_response.content.strip().startswith("["):
                data = json.loads(ai_response.content)
                commands_data = data.get("commands", [])
            else:
                # Parse plain text response
                commands_data = self._parse_text_suggestions(ai_response.content)

            for cmd_data in commands_data[:max_suggestions]:
                suggestion = CommandSuggestion(
                    command=cmd_data.get("command", ""),
                    description=cmd_data.get("description", ""),
                    confidence=self._assess_confidence(cmd_data),
                    safety_level=self._assess_safety(cmd_data.get("command", "")),
                    category=cmd_data.get("category", "general"),
                    complexity=cmd_data.get("complexity", "medium"),
                    examples=cmd_data.get("examples", []),
                    alternatives=cmd_data.get("alternatives", []),
                    warnings=cmd_data.get("warnings", []),
                )
                suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"Failed to parse AI suggestions, using fallback: {e}")
            # Fallback: create a single suggestion from the response
            suggestions = [
                CommandSuggestion(
                    command="# AI response parsing failed",
                    description=ai_response.content[:200],
                    confidence=ConfidenceLevel.LOW,
                    safety_level="safe",
                )
            ]

        return suggestions

    def _parse_command_explanation(
        self,
        ai_response: AIResponse,
        original_command: str,
        include_examples: bool,
        include_alternatives: bool,
    ) -> CommandExplanation:
        """Parse AI response into command explanation."""
        try:
            # Simple parsing - in production, this would be more sophisticated
            content = ai_response.content

            explanation = CommandExplanation(
                command=original_command,
                summary=content.split("\n")[0]
                if content
                else "No explanation available",
                detailed_explanation=content,
                components=self._extract_command_components(original_command),
                examples=self._extract_examples(content) if include_examples else [],
                alternatives=self._extract_alternatives(content)
                if include_alternatives
                else [],
            )

            return explanation

        except Exception as e:
            logger.warning(f"Failed to parse command explanation: {e}")
            return CommandExplanation(
                command=original_command,
                summary="Explanation parsing failed",
                detailed_explanation=ai_response.content,
            )

    def _parse_error_analysis(
        self,
        ai_response: AIResponse,
        command: str,
        error_output: str,
        include_solutions: bool,
        include_prevention: bool,
    ) -> ErrorAnalysis:
        """Parse AI response into error analysis."""
        try:
            content = ai_response.content

            analysis = ErrorAnalysis(
                error_category=self._classify_error(error_output),
                root_cause="Analysis from AI response",
                explanation=content,
                severity=self._assess_error_severity(error_output),
                urgency="medium",
            )

            if include_solutions:
                analysis.immediate_fixes = self._extract_solutions(content)

            if include_prevention:
                analysis.prevention_tips = self._extract_prevention_tips(content)

            return analysis

        except Exception as e:
            logger.warning(f"Failed to parse error analysis: {e}")
            return ErrorAnalysis(
                error_category="unknown",
                root_cause="Analysis parsing failed",
                explanation=ai_response.content,
                severity="medium",
                urgency="low",
            )

    def _parse_command_optimization(
        self,
        ai_response: AIResponse,
        original_command: str,
        include_modern_alternatives: bool,
    ) -> CommandOptimization:
        """Parse AI response into command optimization."""
        try:
            content = ai_response.content

            optimization = CommandOptimization(
                original_command=original_command,
                optimized_commands=[
                    {
                        "command": original_command,
                        "improvement": "AI optimization suggestions",
                        "explanation": content,
                    }
                ],
                performance_analysis={"analysis": content},
                bottlenecks_identified=["See AI analysis"],
                improvements_made=["See AI suggestions"],
            )

            return optimization

        except Exception as e:
            logger.warning(f"Failed to parse command optimization: {e}")
            return CommandOptimization(
                original_command=original_command,
                optimized_commands=[],
                performance_analysis={"error": "Parsing failed"},
                bottlenecks_identified=[],
                improvements_made=[],
            )

    def _calculate_confidence_score(
        self, suggestions: List[CommandSuggestion]
    ) -> float:
        """Calculate overall confidence score for suggestions."""
        if not suggestions:
            return 0.0

        confidence_values = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.6,
            ConfidenceLevel.LOW: 0.3,
        }

        scores = [confidence_values.get(s.confidence, 0.5) for s in suggestions]
        return sum(scores) / len(scores)

    def _calculate_explanation_confidence(
        self, explanation: CommandExplanation
    ) -> float:
        """Calculate confidence score for explanation."""
        # Simple heuristic based on explanation length and detail
        content_length = len(explanation.detailed_explanation)
        component_count = len(explanation.components)

        base_score = min(content_length / 500, 1.0) * 0.6
        detail_score = min(component_count / 5, 1.0) * 0.4

        return base_score + detail_score

    def _calculate_analysis_confidence(self, analysis: ErrorAnalysis) -> float:
        """Calculate confidence score for error analysis."""
        # Simple heuristic
        solution_count = len(analysis.immediate_fixes)
        explanation_length = len(analysis.explanation)

        base_score = min(explanation_length / 300, 1.0) * 0.7
        solution_score = min(solution_count / 3, 1.0) * 0.3

        return base_score + solution_score

    def _calculate_optimization_confidence(
        self, optimization: CommandOptimization
    ) -> float:
        """Calculate confidence score for optimization."""
        optimization_count = len(optimization.optimized_commands)
        improvement_count = len(optimization.improvements_made)

        return min((optimization_count + improvement_count) / 5, 1.0)

    def _assess_confidence(self, cmd_data: Dict[str, Any]) -> ConfidenceLevel:
        """Assess confidence level for a command suggestion."""
        # Simple heuristic - in production, this would be more sophisticated
        command = cmd_data.get("command", "")
        description = cmd_data.get("description", "")

        if len(command) > 5 and len(description) > 20:
            return ConfidenceLevel.HIGH
        elif len(command) > 2 and len(description) > 10:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _assess_safety(self, command: str) -> str:
        """Assess safety level of a command."""
        dangerous_patterns = [
            "rm -rf",
            "dd",
            "mkfs",
            "fdisk",
            "chmod 777",
            "shutdown",
            "reboot",
            "halt",
            ":(){:|:&};:",
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return "dangerous"

        if "sudo" in command_lower or "rm" in command_lower:
            return "caution"

        return "safe"

    def _classify_error(self, error_output: str) -> str:
        """Classify error type."""
        error_lower = error_output.lower()

        if "permission denied" in error_lower:
            return "permission"
        elif "not found" in error_lower:
            return "not_found"
        elif "syntax error" in error_lower:
            return "syntax"
        elif "timeout" in error_lower:
            return "timeout"
        else:
            return "unknown"

    def _assess_error_severity(self, error_output: str) -> str:
        """Assess error severity."""
        error_lower = error_output.lower()

        if any(word in error_lower for word in ["critical", "fatal", "corrupted"]):
            return "critical"
        elif any(word in error_lower for word in ["error", "failed", "denied"]):
            return "high"
        elif any(word in error_lower for word in ["warning", "deprecated"]):
            return "medium"
        else:
            return "low"

    def _classify_model_performance(self, model_data: Dict[str, Any]) -> str:
        """Classify model performance tier."""
        model_id = model_data.get("id", "").lower()

        if "opus" in model_id or "gpt-4" in model_id:
            return "powerful"
        elif "sonnet" in model_id or "gpt-3.5" in model_id:
            return "balanced"
        else:
            return "fast"

    def _parse_text_suggestions(self, text: str) -> List[Dict[str, str]]:
        """Parse plain text into command suggestions."""
        # Simple text parsing - in production, this would be more sophisticated
        lines = text.strip().split("\n")
        suggestions = []

        for line in lines:
            if line.strip():
                if ":" in line:
                    command, description = line.split(":", 1)
                    suggestions.append(
                        {"command": command.strip(), "description": description.strip()}
                    )
                else:
                    suggestions.append(
                        {"command": line.strip(), "description": "AI-generated command"}
                    )

        return suggestions[:5]  # Limit to 5 suggestions

    def _extract_command_components(self, command: str) -> List[Dict[str, str]]:
        """Extract command components."""
        # Simple component extraction
        parts = command.split()
        components = []

        if parts:
            components.append(
                {
                    "type": "command",
                    "value": parts[0],
                    "description": f"Main command: {parts[0]}",
                }
            )

            for part in parts[1:]:
                if part.startswith("-"):
                    components.append(
                        {"type": "flag", "value": part, "description": f"Flag: {part}"}
                    )
                else:
                    components.append(
                        {
                            "type": "argument",
                            "value": part,
                            "description": f"Argument: {part}",
                        }
                    )

        return components

    def _extract_examples(self, content: str) -> List[Dict[str, str]]:
        """Extract examples from AI response."""
        # Simple example extraction
        examples = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if "example" in line.lower() and i + 1 < len(lines):
                examples.append(
                    {"example": lines[i + 1].strip(), "description": "Example usage"}
                )

        return examples[:3]  # Limit to 3 examples

    def _extract_alternatives(self, content: str) -> List[Dict[str, str]]:
        """Extract alternatives from AI response."""
        alternatives = []
        lines = content.split("\n")

        for line in lines:
            if "alternative" in line.lower() and ":" in line:
                _, alt = line.split(":", 1)
                alternatives.append(
                    {"command": alt.strip(), "description": "Alternative approach"}
                )

        return alternatives[:3]  # Limit to 3 alternatives

    def _extract_solutions(self, content: str) -> List[Dict[str, str]]:
        """Extract solutions from error analysis."""
        solutions = []
        lines = content.split("\n")

        for line in lines:
            if any(word in line.lower() for word in ["solution", "fix", "try"]):
                solutions.append(
                    {"solution": line.strip(), "description": "Suggested solution"}
                )

        return solutions[:5]  # Limit to 5 solutions

    def _extract_prevention_tips(self, content: str) -> List[str]:
        """Extract prevention tips from analysis."""
        tips = []
        lines = content.split("\n")

        for line in lines:
            if any(word in line.lower() for word in ["prevent", "avoid", "tip"]):
                tips.append(line.strip())

        return tips[:3]  # Limit to 3 tips
