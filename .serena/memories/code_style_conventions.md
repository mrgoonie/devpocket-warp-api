# DevPocket Code Style & Conventions

## Python Code Style
- **Formatter**: Black (line length 88 characters)
- **Linter**: Ruff for fast Python linting
- **Type Checking**: MyPy with strict type hints
- **Import Style**: Absolute imports preferred
- **String Quotes**: Double quotes for strings

## Naming Conventions
- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: _leading_underscore
- **Database tables**: snake_case (lowercase)

## FastAPI Specific
- **Route handlers**: Use async def for all handlers
- **Dependencies**: Use Depends() for dependency injection
- **Pydantic models**: Use for request/response validation
- **Error handling**: Return appropriate HTTP status codes
- **Documentation**: Include docstrings for all API endpoints

## SQLAlchemy 2.0 Style
- **Models**: Use Mapped[Type] type hints
- **Relationships**: Use relationship() with proper back_populates
- **Queries**: Use async session and select() statements
- **Migrations**: Use Alembic with descriptive names

## Type Hints
- Use type hints for all function parameters and return types
- Use Optional[Type] for nullable fields
- Use List[Type] and Dict[str, Type] for collections
- Import from typing for Python < 3.9 compatibility

## Documentation
- **Docstrings**: Google style docstrings
- **API docs**: Automatic OpenAPI generation via FastAPI
- **Comments**: Explain business logic, not obvious code
- **README**: Keep updated with setup instructions

## Error Handling
- Use try/except blocks with specific exception types
- Log errors with structured logging (structlog)
- Return user-friendly error messages
- Include error codes for client handling

## Security Best Practices
- Never log sensitive data (passwords, tokens)
- Use environment variables for secrets
- Validate all input with Pydantic
- Use parameterized queries (SQLAlchemy handles this)
- Implement proper CORS configuration

## Testing Conventions
- **Test files**: test_*.py pattern
- **Test classes**: TestClassName pattern  
- **Test methods**: test_method_name pattern
- **Fixtures**: Use pytest fixtures for setup
- **Async tests**: Use pytest-asyncio for async test support