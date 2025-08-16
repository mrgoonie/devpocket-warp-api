"""
Pydantic schemas for AI service endpoints.

Contains request and response models for AI-powered features using BYOK model.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, validator
from enum import Enum


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
    account_info: Optional[Dict[str, Any]] = Field(
        None, description="Account information"
    )
    models_available: Optional[int] = Field(
        None, description="Number of available models"
    )
    recommended_models: Optional[List[str]] = Field(
        None, description="Recommended models for DevPocket"
    )
    error: Optional[str] = Field(
        None, description="Error message if validation failed"
    )
    timestamp: datetime = Field(..., description="Validation timestamp")


class AIUsageStats(BaseModel):
    """Schema for AI usage statistics."""

    usage: float = Field(..., description="Current usage amount")
    limit: Optional[float] = Field(None, description="Usage limit")
    is_free_tier: bool = Field(..., description="Whether using free tier")
    requests_today: int = Field(default=0, description="Requests made today")
    tokens_used: int = Field(default=0, description="Total tokens used")
    cost_estimate: Optional[float] = Field(None, description="Estimated cost")
    rate_limit: Dict[str, Any] = Field(
        ..., description="Rate limit information"
    )
    timestamp: datetime = Field(..., description="Stats timestamp")


# Command Suggestion Schemas
class CommandSuggestionRequest(BaseModel):
    """Schema for command suggestion request."""

    api_key: str = Field(
        ..., min_length=10, description="User's OpenRouter API key"
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Natural language description",
    )

    # Context information
    working_directory: Optional[str] = Field(
        None, description="Current working directory"
    )
    previous_commands: Optional[List[str]] = Field(
        None, max_items=10, description="Recent commands"
    )
    operating_system: Optional[str] = Field(
        None, description="Operating system"
    )
    shell_type: Optional[str] = Field(
        default="bash", description="Shell type (bash, zsh, fish, etc.)"
    )
    user_level: Optional[str] = Field(
        default="intermediate", description="User experience level"
    )

    # AI settings
    model: Optional[AIModel] = Field(None, description="Specific model to use")
    max_suggestions: int = Field(
        default=5, ge=1, le=10, description="Maximum number of suggestions"
    )
    include_explanations: bool = Field(
        default=True, description="Include command explanations"
    )


class CommandSuggestion(BaseModel):
    """Schema for a single command suggestion."""

    command: str = Field(..., description="Suggested command")
    description: str = Field(
        ..., description="Description of what the command does"
    )
    confidence: ConfidenceLevel = Field(..., description="Confidence level")
    safety_level: str = Field(
        ..., description="Safety level (safe, caution, dangerous)"
    )

    # Additional details
    examples: Optional[List[str]] = Field(
        default=[], description="Usage examples"
    )
    alternatives: Optional[List[str]] = Field(
        default=[], description="Alternative commands"
    )
    prerequisites: Optional[List[str]] = Field(
        default=[], description="Prerequisites or dependencies"
    )
    warnings: Optional[List[str]] = Field(
        default=[], description="Safety warnings"
    )

    # Metadata
    category: str = Field(default="general", description="Command category")
    complexity: str = Field(
        default="medium",
        description="Complexity level (simple, medium, complex)",
    )


class CommandSuggestionResponse(BaseModel):
    """Schema for command suggestion response."""

    suggestions: List[CommandSuggestion] = Field(
        ..., description="List of command suggestions"
    )

    # Request context
    query_description: str = Field(
        ..., description="Original query description"
    )
    context_used: Dict[str, Any] = Field(
        ..., description="Context information used"
    )

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(
        ..., description="Response time in milliseconds"
    )
    tokens_used: Dict[str, int] = Field(
        ..., description="Token usage breakdown"
    )

    # Quality indicators
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Overall confidence score"
    )
    processing_notes: Optional[List[str]] = Field(
        None, description="Processing notes or warnings"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# Command Explanation Schemas
class CommandExplanationRequest(BaseModel):
    """Schema for command explanation request."""

    api_key: str = Field(
        ..., min_length=10, description="User's OpenRouter API key"
    )
    command: str = Field(
        ..., min_length=1, max_length=2000, description="Command to explain"
    )

    # Context
    working_directory: Optional[str] = Field(
        None, description="Command context directory"
    )
    user_level: Optional[str] = Field(
        default="intermediate", description="User experience level"
    )
    include_examples: bool = Field(
        default=True, description="Include usage examples"
    )
    include_alternatives: bool = Field(
        default=True, description="Include alternative commands"
    )

    # AI settings
    model: Optional[AIModel] = Field(None, description="Specific model to use")
    detail_level: str = Field(
        default="medium", description="Detail level (basic, medium, detailed)"
    )


class CommandExplanation(BaseModel):
    """Schema for command explanation."""

    command: str = Field(..., description="Original command")
    summary: str = Field(
        ..., description="Brief summary of what the command does"
    )
    detailed_explanation: str = Field(..., description="Detailed explanation")

    # Command breakdown
    components: List[Dict[str, str]] = Field(
        default=[], description="Command components breakdown"
    )
    parameters: List[Dict[str, Any]] = Field(
        default=[], description="Parameters and flags explanation"
    )

    # Additional information
    examples: List[Dict[str, str]] = Field(
        default=[], description="Usage examples with descriptions"
    )
    alternatives: List[Dict[str, str]] = Field(
        default=[], description="Alternative commands"
    )
    related_commands: List[str] = Field(
        default=[], description="Related commands"
    )

    # Safety and best practices
    safety_notes: List[str] = Field(
        default=[], description="Safety considerations"
    )
    best_practices: List[str] = Field(
        default=[], description="Best practice recommendations"
    )
    common_mistakes: List[str] = Field(
        default=[], description="Common mistakes to avoid"
    )


class CommandExplanationResponse(BaseModel):
    """Schema for command explanation response."""

    explanation: CommandExplanation = Field(
        ..., description="Command explanation"
    )

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(
        ..., description="Response time in milliseconds"
    )
    tokens_used: Dict[str, int] = Field(
        ..., description="Token usage breakdown"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Explanation confidence score"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# Error Analysis Schemas
class ErrorAnalysisRequest(BaseModel):
    """Schema for error analysis request."""

    api_key: str = Field(
        ..., min_length=10, description="User's OpenRouter API key"
    )
    command: str = Field(
        ..., min_length=1, max_length=2000, description="Failed command"
    )
    error_output: str = Field(..., description="Error output from command")

    # Context
    exit_code: Optional[int] = Field(None, description="Command exit code")
    working_directory: Optional[str] = Field(
        None, description="Working directory"
    )
    environment_info: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    system_info: Optional[Dict[str, str]] = Field(
        None, description="System information"
    )

    # Analysis preferences
    include_solutions: bool = Field(
        default=True, description="Include solution suggestions"
    )
    include_prevention: bool = Field(
        default=True, description="Include prevention tips"
    )

    # AI settings
    model: Optional[AIModel] = Field(None, description="Specific model to use")


class ErrorAnalysis(BaseModel):
    """Schema for error analysis."""

    error_category: str = Field(
        ..., description="Error category (permission, not_found, syntax, etc.)"
    )
    root_cause: str = Field(
        ..., description="Identified root cause of the error"
    )
    explanation: str = Field(
        ..., description="Detailed explanation of why the error occurred"
    )

    # Solutions
    immediate_fixes: List[Dict[str, str]] = Field(
        default=[], description="Immediate fix suggestions"
    )
    alternative_approaches: List[Dict[str, str]] = Field(
        default=[], description="Alternative approaches"
    )
    troubleshooting_steps: List[str] = Field(
        default=[], description="Step-by-step troubleshooting"
    )

    # Prevention
    prevention_tips: List[str] = Field(
        default=[], description="Prevention recommendations"
    )
    best_practices: List[str] = Field(
        default=[], description="Best practices to avoid similar errors"
    )

    # Additional context
    related_errors: List[str] = Field(
        default=[], description="Related error patterns"
    )
    resources: List[Dict[str, str]] = Field(
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
    response_time_ms: int = Field(
        ..., description="Response time in milliseconds"
    )
    tokens_used: Dict[str, int] = Field(
        ..., description="Token usage breakdown"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Analysis confidence score"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# Command Optimization Schemas
class CommandOptimizationRequest(BaseModel):
    """Schema for command optimization request."""

    api_key: str = Field(
        ..., min_length=10, description="User's OpenRouter API key"
    )
    command: str = Field(
        ..., min_length=1, max_length=2000, description="Command to optimize"
    )

    # Context
    usage_frequency: Optional[str] = Field(
        None, description="How often the command is used"
    )
    performance_issues: Optional[str] = Field(
        None, description="Specific performance concerns"
    )
    environment: Optional[str] = Field(None, description="Target environment")
    constraints: Optional[List[str]] = Field(
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
    model: Optional[AIModel] = Field(None, description="Specific model to use")


class CommandOptimization(BaseModel):
    """Schema for command optimization."""

    original_command: str = Field(..., description="Original command")
    optimized_commands: List[Dict[str, Any]] = Field(
        ..., description="Optimized alternatives"
    )

    # Analysis
    performance_analysis: Dict[str, Any] = Field(
        ..., description="Performance analysis"
    )
    bottlenecks_identified: List[str] = Field(
        default=[], description="Identified bottlenecks"
    )
    improvements_made: List[str] = Field(
        default=[], description="Improvements in optimized versions"
    )

    # Recommendations
    best_practices: List[str] = Field(
        default=[], description="Best practice recommendations"
    )
    modern_alternatives: List[Dict[str, str]] = Field(
        default=[], description="Modern tool alternatives"
    )

    # Trade-offs
    trade_offs: List[Dict[str, str]] = Field(
        default=[], description="Trade-offs to consider"
    )
    compatibility_notes: List[str] = Field(
        default=[], description="Compatibility considerations"
    )


class CommandOptimizationResponse(BaseModel):
    """Schema for command optimization response."""

    optimization: CommandOptimization = Field(
        ..., description="Command optimization"
    )

    # AI metadata
    model_used: str = Field(..., description="AI model used")
    response_time_ms: int = Field(
        ..., description="Response time in milliseconds"
    )
    tokens_used: Dict[str, int] = Field(
        ..., description="Token usage breakdown"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Optimization confidence score"
    )

    timestamp: datetime = Field(..., description="Response timestamp")


# AI Service Settings Schemas
class AISettings(BaseModel):
    """Schema for AI service settings."""

    preferred_models: Dict[str, str] = Field(
        default={}, description="Preferred models for different tasks"
    )
    default_model: Optional[str] = Field(None, description="Default model")

    # Response preferences
    max_suggestions: int = Field(
        default=5, ge=1, le=10, description="Maximum suggestions"
    )
    detail_level: str = Field(
        default="medium", description="Default detail level"
    )
    include_examples: bool = Field(
        default=True, description="Include examples by default"
    )
    include_warnings: bool = Field(
        default=True, description="Include safety warnings"
    )

    # Usage preferences
    auto_validate_key: bool = Field(
        default=True, description="Auto-validate API key"
    )
    cache_responses: bool = Field(
        default=True, description="Cache AI responses"
    )
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
    supports_vision: bool = Field(
        default=False, description="Supports image analysis"
    )

    # Pricing
    pricing: Dict[str, str] = Field(..., description="Pricing information")

    # Provider info
    provider: str = Field(..., description="Model provider")
    architecture: Dict[str, Any] = Field(
        default={}, description="Architecture information"
    )

    # Usage recommendations
    recommended_for: List[str] = Field(
        default=[], description="Recommended use cases"
    )
    performance_tier: str = Field(
        ..., description="Performance tier (fast, balanced, powerful)"
    )


class AvailableModelsResponse(BaseModel):
    """Schema for available models response."""

    models: List[AIModelInfo] = Field(..., description="Available models")
    total_models: int = Field(..., description="Total number of models")
    recommended_models: List[str] = Field(
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
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    suggestions: Optional[List[str]] = Field(
        None, description="Suggestions to fix the error"
    )
    timestamp: datetime = Field(..., description="Error timestamp")


# Batch Processing Schemas
class BatchAIRequest(BaseModel):
    """Schema for batch AI processing request."""

    api_key: str = Field(
        ..., min_length=10, description="User's OpenRouter API key"
    )
    requests: List[Dict[str, Any]] = Field(
        ..., min_items=1, max_items=10, description="Batch requests"
    )
    service_type: AIServiceType = Field(..., description="Type of AI service")
    model: Optional[AIModel] = Field(
        None, description="Model to use for all requests"
    )


class BatchAIResponse(BaseModel):
    """Schema for batch AI processing response."""

    results: List[Dict[str, Any]] = Field(..., description="Batch results")
    success_count: int = Field(
        ..., description="Number of successful requests"
    )
    error_count: int = Field(..., description="Number of failed requests")
    total_tokens_used: int = Field(..., description="Total tokens used")
    total_response_time_ms: int = Field(
        ..., description="Total processing time"
    )
    timestamp: datetime = Field(..., description="Response timestamp")
