# Task Completion Checklist

When completing any development task in DevPocket, ensure the following steps are completed:

## Code Quality
- [ ] Code is formatted with `black .`
- [ ] Code passes linting with `ruff check --fix .`
- [ ] Type hints are added and pass `mypy .` checks
- [ ] Code follows project conventions (see code_style_conventions.md)

## Testing
- [ ] Unit tests are written for new functionality
- [ ] All tests pass with `pytest`
- [ ] Test coverage is maintained (use `pytest --cov`)
- [ ] Integration tests added for API endpoints

## Security & Validation
- [ ] Input validation implemented with Pydantic models
- [ ] Proper error handling with try/catch blocks
- [ ] Security best practices followed (no secrets in logs, etc.)
- [ ] Authentication/authorization correctly implemented

## Documentation
- [ ] Docstrings added to all new functions/classes
- [ ] API endpoints documented with proper OpenAPI annotations
- [ ] Update relevant documentation files if needed
- [ ] Comments added for complex business logic

## Database (if applicable)
- [ ] Database migrations created and tested
- [ ] Models follow SQLAlchemy 2.0 patterns
- [ ] Repository methods are properly implemented
- [ ] Database queries are optimized

## Integration
- [ ] New routes/dependencies properly registered with FastAPI
- [ ] Environment variables added to configuration
- [ ] Dependencies updated in requirements.txt if needed
- [ ] Proper logging added for debugging

## Final Steps
- [ ] Manual testing performed
- [ ] Git commit with conventional commit format
- [ ] No hardcoded values or debug code left in
- [ ] Performance considerations evaluated

## Commit Message Format
Use conventional commits:
- `feat: add user authentication system`
- `fix: resolve password validation issue`
- `docs: update API endpoint documentation`
- `refactor: improve error handling structure`