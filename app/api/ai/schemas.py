"""
Pydantic schemas for AI service endpoints.

Contains request and response models for AI-powered features using BYOK model.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class AIModel(str, Enum):
    """Supported AI models."""

    GEMINI_2_5_FLASH = "google/gemini-2.5-flash"
    GEMINI_2_5_PRO = "google/gemini-2.5-pro"


class AIServiceType(str, Enum):
    """AI service types."""

    COMMAND_SUGGESTION = "command_suggestion"
    COMMAND_EXPLANATION = "command_explanation"
    ERROR_ANALYSIS = "error_analysis"
    COMMAND_OPTIMIZATION = "optimization"


class ConfidenceLevel(str, Enum):
    """Confidence levels for AI responses."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# API Key Management Schemas
class APIKeyValidation(BaseModel):
    """Schema for API key validation request."""

    api_key: str = Field(
        ..., min_length=10, description="OpenRouter API key to validate"
    )


class APIKeyValidationResponse(BaseModel):
    """Schema for API key validation response."""

    valid: bool = Field(..., description="Whether the API key is valid")
    account_info: dict[str, Any] | None = Field(None, description="Account information")
    models_available: int | None = Field(None, description="Number of available models")
    recommended_models: list[str] | None = Field(
        None, description="Recommended models for DevPocket"
    )
    error: str | None = Field(
        default=None, description="Error message if validation failed"
    )
    timestamp: datetime = Field(..., description="Validation timestamp")


class AIUsageStats(BaseModel):
    """Schema for AI usage statistics."""

    usage: float = Field(..., description="Current usage amount")
    limit: float | None = Field(default=None, description="Usage limit")
    is_free_tier: bool = Field(..., description="Whether using free tier")
    requests_today: int = Field(default=0, description="Requests made today")
    tokens_used: int = Field(default=0, description="Total tokens used")
    cost_estimate: float | None = Field(default=None, description="Estimated cost")
    rate_limit: dict[str, Any] = Field(..., description="Rate limit information")
    timestamp: datetime = Field(..., description="Stats timestamp")


# Command Suggestion Schemas
class CommandSuggestionRequest(BaseModel):
    """Schema for command suggestion request."""

    api_key: str = Field(..., min_length=10, description="User's OpenRouter API key")
    description: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Natural language description",
    )

    # Context information
    working_directory: str | None = Field(None, description="Current working directory")
    previous_commands: Annotated[list[str], Field(max_length=10)] | None = Field(
        None, description="Recent commands"
    )
    operating_system: str | None = Field(default=None, description="Operating system")
    shell_type: str | None = Field(
        default="bash", description="Shell type (bash, zsh, fish, etc.)"
    )
    user_level: str | None = Field(
        default="intermediate", description="User experience level"
    )

    # AI settings
    model: AIModel | None = Field(default=None, description="Specific model to use")
    max_suggestions: int = Field(
        default=5, ge=1, le=10, description="Maximum number of suggestions"
    )
    include_explanations: bool = Field(
        default=True, description="Include command explanations"
    )


class CommandSuggestion(BaseModel):
    """Schema for a single command suggestion."""

    command: str = Field(..., description="Suggested command")
    description: str = Field(..., description="Description of what the command does")
    confidence: ConfidenceLevel = Field(..., description="Confidence level")
    safety_level: str = Field(
        ..., description="Safety level (safe, caution, dangerous)"
    )

    # Additional details
    examples: list[str] | None = Field(default=[], description="Usage examples")
    alternatives: list[str] | None = Field(
        default=[], description="Alternative commands"
    )
    prerequisites: list[str] | None = Field(
        default=[], description="Prerequisites or dependencies"
    )
    warnings: list[str] | None = Field(default=[], description="Safety warnings")

    # Metadata
    category: str = Field(default="general", description="Command category")
    complexity: str = Field(
        default="medium",
        description="Complexity level (simple, medium, complex)",
    )


class CommandSuggestionResponse(BaseModel):
    """Schema for command suggestion response."""

    suggestions: list[CommandSuggestion] = Field(
        ..., description="List of command suggestions"
    )

    # Request context
    query_description: str = Field(..., description="Original query description")
    context_used: dict[str, Any] = Field(..., description="Context information used")

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    tokens_used: dict[str, int] = Field(..., description="Token usage breakdown")

    # Quality indicators
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Overall confidence score"
    )
    processing_notes: list[str] | None = Field(
        None, description="Processing notes or warnings"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# Command Explanation Schemas
class CommandExplanationRequest(BaseModel):
    """Schema for command explanation request."""

    api_key: str = Field(..., min_length=10, description="User's OpenRouter API key")
    command: str = Field(
        ..., min_length=1, max_length=2000, description="Command to explain"
    )

    # Context
    working_directory: str | None = Field(None, description="Command context directory")
    user_level: str | None = Field(
        default="intermediate", description="User experience level"
    )
    include_examples: bool = Field(default=True, description="Include usage examples")
    include_alternatives: bool = Field(
        default=True, description="Include alternative commands"
    )

    # AI settings
    model: AIModel | None = Field(default=None, description="Specific model to use")
    detail_level: str = Field(
        default="medium", description="Detail level (basic, medium, detailed)"
    )


class CommandExplanation(BaseModel):
    """Schema for command explanation."""

    command: str = Field(..., description="Original command")
    summary: str = Field(..., description="Brief summary of what the command does")
    detailed_explanation: str = Field(..., description="Detailed explanation")

    # Command breakdown
    components: list[dict[str, str]] = Field(
        default=[], description="Command components breakdown"
    )
    parameters: list[dict[str, Any]] = Field(
        default=[], description="Parameters and flags explanation"
    )

    # Additional information
    examples: list[dict[str, str]] = Field(
        default=[], description="Usage examples with descriptions"
    )
    alternatives: list[dict[str, str]] = Field(
        default=[], description="Alternative commands"
    )
    related_commands: list[str] = Field(default=[], description="Related commands")

    # Safety and best practices
    safety_notes: list[str] = Field(default=[], description="Safety considerations")
    best_practices: list[str] = Field(
        default=[], description="Best practice recommendations"
    )
    common_mistakes: list[str] = Field(
        default=[], description="Common mistakes to avoid"
    )


class CommandExplanationResponse(BaseModel):
    """Schema for command explanation response."""

    explanation: CommandExplanation = Field(..., description="Command explanation")

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    tokens_used: dict[str, int] = Field(..., description="Token usage breakdown")
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Explanation confidence score"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# Error Analysis Schemas
class ErrorAnalysisRequest(BaseModel):
    """Schema for error analysis request."""

    api_key: str = Field(..., min_length=10, description="User's OpenRouter API key")
    command: str = Field(
        ..., min_length=1, max_length=2000, description="Failed command"
    )
    error_output: str = Field(..., description="Error output from command")

    # Context
    exit_code: int | None = Field(default=None, description="Command exit code")
    working_directory: str | None = Field(default=None, description="Working directory")
    environment_info: dict[str, str] | None = Field(
        None, description="Environment variables"
    )
    system_info: dict[str, str] | None = Field(None, description="System information")

    # Analysis preferences
    include_solutions: bool = Field(
        default=True, description="Include solution suggestions"
    )
    include_prevention: bool = Field(
        default=True, description="Include prevention tips"
    )

    # AI settings
    model: AIModel | None = Field(default=None, description="Specific model to use")


class ErrorAnalysis(BaseModel):
    """Schema for error analysis."""

    error_category: str = Field(
        ..., description="Error category (permission, not_found, syntax, etc.)"
    )
    root_cause: str = Field(..., description="Identified root cause of the error")
    explanation: str = Field(
        ..., description="Detailed explanation of why the error occurred"
    )

    # Solutions
    immediate_fixes: list[dict[str, str]] = Field(
        default=[], description="Immediate fix suggestions"
    )
    alternative_approaches: list[dict[str, str]] = Field(
        default=[], description="Alternative approaches"
    )
    troubleshooting_steps: list[str] = Field(
        default=[], description="Step-by-step troubleshooting"
    )

    # Prevention
    prevention_tips: list[str] = Field(
        default=[], description="Prevention recommendations"
    )
    best_practices: list[str] = Field(
        default=[], description="Best practices to avoid similar errors"
    )

    # Additional context
    related_errors: list[str] = Field(default=[], description="Related error patterns")
    resources: list[dict[str, str]] = Field(
        default=[], description="Additional resources or documentation"
    )

    # Severity assessment
    severity: str = Field(
        ..., description="Error severity (low, medium, high, critical)"
    )
    urgency: str = Field(..., description="Fix urgency (low, medium, high)")


class ErrorAnalysisResponse(BaseModel):
    """Schema for error analysis response."""

    analysis: ErrorAnalysis = Field(..., description="Error analysis")

    # Original context
    original_command: str = Field(..., description="Original failed command")
    error_summary: str = Field(..., description="Brief error summary")

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    tokens_used: dict[str, int] = Field(..., description="Token usage breakdown")
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Analysis confidence score"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# Command Optimization Schemas
class CommandOptimizationRequest(BaseModel):
    """Schema for command optimization request."""

    api_key: str = Field(..., min_length=10, description="User's OpenRouter API key")
    command: str = Field(
        ..., min_length=1, max_length=2000, description="Command to optimize"
    )

    # Context
    usage_frequency: str | None = Field(
        None, description="How often the command is used"
    )
    performance_issues: str | None = Field(
        None, description="Specific performance concerns"
    )
    environment: str | None = Field(default=None, description="Target environment")
    constraints: list[str] | None = Field(
        None, description="Any constraints or limitations"
    )

    # Optimization preferences
    optimize_for: str = Field(
        default="performance",
        description="Optimization target (performance, safety, readability)",
    )
    include_modern_alternatives: bool = Field(
        default=True, description="Include modern tool alternatives"
    )

    # AI settings
    model: AIModel | None = Field(default=None, description="Specific model to use")


class CommandOptimization(BaseModel):
    """Schema for command optimization."""

    original_command: str = Field(..., description="Original command")
    optimized_commands: list[dict[str, Any]] = Field(
        ..., description="Optimized alternatives"
    )

    # Analysis
    performance_analysis: dict[str, Any] = Field(
        ..., description="Performance analysis"
    )
    bottlenecks_identified: list[str] = Field(
        default=[], description="Identified bottlenecks"
    )
    improvements_made: list[str] = Field(
        default=[], description="Improvements in optimized versions"
    )

    # Recommendations
    best_practices: list[str] = Field(
        default=[], description="Best practice recommendations"
    )
    modern_alternatives: list[dict[str, str]] = Field(
        default=[], description="Modern tool alternatives"
    )

    # Trade-offs
    trade_offs: list[dict[str, str]] = Field(
        default=[], description="Trade-offs to consider"
    )
    compatibility_notes: list[str] = Field(
        default=[], description="Compatibility considerations"
    )


class CommandOptimizationResponse(BaseModel):
    """Schema for command optimization response."""

    optimization: CommandOptimization = Field(..., description="Command optimization")

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    tokens_used: dict[str, int] = Field(..., description="Token usage breakdown")
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Optimization confidence score"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# AI Service Settings Schemas
class AISettings(BaseModel):
    """Schema for AI service settings."""

    preferred_models: dict[str, str] = Field(
        default={}, description="Preferred models for different tasks"
    )
    default_model: str | None = Field(default=None, description="Default model")

    # Response preferences
    max_suggestions: int = Field(
        default=5, ge=1, le=10, description="Maximum suggestions"
    )
    detail_level: str = Field(default="medium", description="Default detail level")
    include_examples: bool = Field(
        default=True, description="Include examples by default"
    )
    include_warnings: bool = Field(default=True, description="Include safety warnings")

    # Usage preferences
    auto_validate_key: bool = Field(default=True, description="Auto-validate API key")
    cache_responses: bool = Field(default=True, description="Cache AI responses")
    timeout_seconds: int = Field(
        default=30, ge=5, le=120, description="Request timeout"
    )


class AISettingsResponse(AISettings):
    """Schema for AI settings response."""

    user_id: str = Field(..., description="User ID")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


# Model Information Schemas
class AIModelInfo(BaseModel):
    """Schema for AI model information."""

    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model name")
    description: str = Field(..., description="Model description")

    # Capabilities
    context_length: int = Field(..., description="Maximum context length")
    supports_function_calling: bool = Field(
        default=False, description="Supports function calling"
    )
    supports_vision: bool = Field(default=False, description="Supports image analysis")

    # Pricing
    pricing: dict[str, str] = Field(..., description="Pricing information")

    # Provider info
    provider: str = Field(..., description="Model provider")
    architecture: dict[str, Any] = Field(
        default={}, description="Architecture information"
    )

    # Usage recommendations
    recommended_for: list[str] = Field(default=[], description="Recommended use cases")
    performance_tier: str = Field(
        ..., description="Performance tier (fast, balanced, powerful)"
    )


class AvailableModelsResponse(BaseModel):
    """Schema for available models response."""

    models: list[AIModelInfo] = Field(..., description="Available models")
    total_models: int = Field(..., description="Total number of models")
    recommended_models: list[str] = Field(
        ..., description="Recommended models for DevPocket"
    )
    timestamp: datetime = Field(..., description="Response timestamp")


# Common Response Schemas
class MessageResponse(BaseModel):
    """Schema for simple message responses."""

    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class AIErrorResponse(BaseModel):
    """Schema for AI service error responses."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    suggestions: list[str] | None = Field(
        None, description="Suggestions to fix the error"
    )
    timestamp: datetime = Field(..., description="Error timestamp")


# Batch Processing Schemas
class BatchAIRequest(BaseModel):
    """Schema for batch AI processing request."""

    api_key: str = Field(..., min_length=10, description="User's OpenRouter API key")
    requests: Annotated[
        list[dict[str, Any]],
        Field(min_length=1, max_length=10, description="Batch requests"),
    ]
    service_type: AIServiceType = Field(..., description="Type of AI service")
    model: AIModel | None = Field(
        default=None, description="Model to use for all requests"
    )


class BatchAIResponse(BaseModel):
    """Schema for batch AI processing response."""

    results: list[dict[str, Any]] = Field(..., description="Batch results")
    success_count: int = Field(..., description="Number of successful requests")
    error_count: int = Field(..., description="Number of failed requests")
    total_tokens_used: int = Field(..., description="Total tokens used")
    total_response_time_ms: int = Field(..., description="Total processing time")
    timestamp: datetime = Field(..., description="Response timestamp")
