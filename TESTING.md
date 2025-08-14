# DevPocket API Testing Suite

This document provides comprehensive information about the testing infrastructure, test execution, and quality standards for the DevPocket API.

## Overview

The DevPocket API testing suite is designed to ensure production readiness through comprehensive test coverage, automated quality gates, and continuous integration. The test suite achieves 80%+ coverage across all critical components.

## Test Structure

```
tests/
├── conftest.py                 # Global test configuration and fixtures
├── pytest.ini                 # Pytest configuration
├── factories/                 # Factory Boy test data generators
│   ├── user_factory.py        # User and UserSettings factories
│   ├── session_factory.py     # Terminal session factories
│   ├── ssh_factory.py         # SSH profile and key factories
│   ├── command_factory.py     # Command execution factories
│   └── sync_factory.py        # Sync data factories
├── test_database/             # Database layer tests
│   ├── test_models.py         # SQLAlchemy model tests
│   ├── test_repositories.py   # Repository pattern tests
│   └── test_migrations.py     # Database migration tests
├── test_auth/                 # Authentication and security tests
│   ├── test_security.py       # JWT and password security
│   ├── test_dependencies.py   # Auth middleware tests
│   └── test_endpoints.py      # Auth API endpoint tests
├── test_api/                  # API endpoint tests
│   ├── test_ssh_endpoints.py  # SSH management API
│   ├── test_sessions_endpoints.py # Session management API
│   ├── test_commands_endpoints.py # Command API
│   ├── test_ai_endpoints.py   # AI service API (BYOK)
│   ├── test_sync_endpoints.py # Synchronization API
│   └── test_profile_endpoints.py # Profile management API
├── test_websocket/            # WebSocket functionality tests
│   ├── test_manager.py        # Connection manager tests
│   ├── test_terminal.py       # Terminal functionality tests
│   ├── test_protocols.py      # Message protocol tests
│   └── test_ssh_integration.py # SSH WebSocket integration
├── test_services/             # Service layer tests
│   ├── test_ssh_client.py     # SSH service testing
│   ├── test_openrouter.py     # AI service testing
│   └── test_terminal_service.py # Terminal services
├── integration/               # End-to-end integration tests
│   ├── test_api_flows.py      # Complete API workflows
│   ├── test_websocket_flows.py # WebSocket integration flows
│   └── test_user_journeys.py  # Full user scenarios
├── security/                  # Security testing
│   ├── test_input_validation.py # Input sanitization tests
│   ├── test_authorization.py   # Access control tests
│   └── test_security_headers.py # Security middleware tests
└── performance/               # Performance testing
    ├── test_load.py           # Load testing scenarios
    ├── test_stress.py         # Stress testing
    └── test_websocket_performance.py # WebSocket performance
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Database Models**: Test all SQLAlchemy models, relationships, and business logic
- **Repositories**: Test CRUD operations, queries, and data validation
- **Authentication**: JWT tokens, password security, and session management
- **Services**: Business logic, external integrations, and utility functions

### Integration Tests (`@pytest.mark.integration`)
- **API Workflows**: End-to-end API request/response flows
- **Database Integration**: Multi-table operations and transactions
- **Service Integration**: External service interactions (mocked)
- **WebSocket Integration**: Real-time communication testing

### Security Tests (`@pytest.mark.security`)
- **Input Validation**: SQL injection, XSS, and command injection prevention
- **Authentication**: Token security, password strength, rate limiting
- **Authorization**: Access control and permission validation
- **Security Headers**: CORS, CSP, and other security middleware

### Performance Tests (`@pytest.mark.performance`)
- **Load Testing**: API endpoint performance under load
- **WebSocket Performance**: Concurrent connection handling
- **Database Performance**: Query optimization and response times
- **Memory Usage**: Resource consumption monitoring

## Running Tests

### Prerequisites

1. **Python Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   ```bash
   # Start PostgreSQL test database
   docker run --name postgres-test -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=devpocket_test -p 5433:5432 -d postgres:15
   
   # Start Redis test instance
   docker run --name redis-test -p 6380:6379 -d redis:7-alpine
   ```

3. **Environment Variables**:
   ```bash
   export ENVIRONMENT=test
   export TESTING=true
   export DATABASE_URL=postgresql://test:test@localhost:5433/devpocket_test
   export REDIS_URL=redis://localhost:6380
   export JWT_SECRET_KEY=test_secret_key_for_testing_only
   ```

### Test Execution

#### Run All Tests
```bash
# Full test suite with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=80

# Parallel execution (faster)
pytest -n auto --cov=app --cov-report=html

# With detailed output
pytest -v --tb=short --durations=10
```

#### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Security tests
pytest -m security

# Performance tests
pytest -m performance

# API endpoint tests
pytest -m api

# WebSocket tests
pytest -m websocket

# Database tests
pytest -m database

# Authentication tests
pytest -m auth
```

#### Run Specific Test Files
```bash
# Database model tests
pytest tests/test_database/test_models.py

# Authentication tests
pytest tests/test_auth/

# SSH API tests
pytest tests/test_api/test_ssh_endpoints.py

# WebSocket tests
pytest tests/test_websocket/
```

#### Run Tests with Coverage
```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html
```

### Debugging Tests

#### Running Specific Tests
```bash
# Run single test
pytest tests/test_auth/test_security.py::TestPasswordSecurity::test_password_hashing -v

# Run with debugger
pytest --pdb tests/test_auth/test_security.py::TestPasswordSecurity::test_password_hashing

# Run with print statements
pytest -s tests/test_auth/test_security.py
```

#### Test Data Inspection
```bash
# Show test database state
pytest --setup-show tests/test_database/

# Keep test database after failure
pytest --tb=long --maxfail=1 tests/test_database/
```

## Test Configuration

### pytest.ini
- **Coverage Settings**: 80% minimum coverage requirement
- **Test Discovery**: Automatic test file and function discovery
- **Markers**: Categorization of tests by type and functionality
- **Asyncio**: Automatic async test handling
- **Environment**: Test-specific environment variables

### .coveragerc
- **Source Tracking**: Monitors app/ directory for coverage
- **Exclusions**: Omits migrations, test files, and boilerplate code
- **Reporting**: HTML, XML, and terminal coverage reports
- **Branch Coverage**: Tracks conditional code paths

### conftest.py
- **Database Fixtures**: Test database setup and cleanup
- **Authentication Fixtures**: User creation and token generation
- **Mock Services**: External service mocking (Redis, OpenRouter)
- **WebSocket Fixtures**: WebSocket connection testing utilities

## Test Data Management

### Factory Boy Factories
- **UserFactory**: Creates test users with various configurations
- **SessionFactory**: Generates terminal sessions and SSH connections
- **SSHProfileFactory**: Creates SSH server profiles and configurations
- **CommandFactory**: Generates command execution records
- **SyncDataFactory**: Creates synchronization data across devices

### Test Data Cleanup
- **Automatic Rollback**: Each test runs in a transaction that's rolled back
- **Fresh Database**: Clean database state for every test
- **No Data Leakage**: Tests are isolated and don't affect each other

## Mocking Strategy

### External Services
- **OpenRouter API**: Mocked AI service responses for testing
- **SSH Servers**: Simulated SSH connections and responses
- **Redis**: Mock caching and session storage
- **Email Services**: Mocked email sending for notifications

### Internal Services
- **File System**: Mocked file operations for SSH keys
- **Time**: Controlled time for testing time-sensitive operations
- **Random Generation**: Deterministic random values for reproducible tests

## Quality Standards

### Coverage Requirements
- **Overall**: 80% minimum code coverage
- **Critical Paths**: 90% coverage for authentication and security
- **Security Code**: 100% coverage for security-related functions
- **New Code**: All new code must include comprehensive tests

### Performance Benchmarks
- **API Response Time**: < 200ms for simple endpoints
- **Database Queries**: < 50ms for single record operations
- **WebSocket Latency**: < 10ms for message processing
- **Memory Usage**: < 100MB peak memory during test execution

### Security Validation
- **Input Sanitization**: All user inputs tested for injection attacks
- **Authentication**: Token security and session management validation
- **Authorization**: Access control and permission testing
- **Data Protection**: Sensitive data handling and encryption validation

## Continuous Integration

### GitHub Actions Workflow
- **Matrix Testing**: Python 3.11 and 3.12 compatibility
- **Service Dependencies**: PostgreSQL and Redis containers
- **Database Migrations**: Automatic migration testing
- **Code Quality**: Linting, formatting, and type checking
- **Security Scanning**: Bandit, Safety, and Semgrep analysis
- **Coverage Reporting**: Codecov integration for coverage tracking

### Quality Gates
- **Test Pass Rate**: 100% test success requirement
- **Coverage Threshold**: 80% minimum coverage enforcement
- **Security Scan**: No high-severity security issues
- **Performance**: Response time thresholds must be met
- **Code Quality**: Linting and formatting standards compliance

### Deployment Pipeline
- **Staging Deployment**: Automatic deployment on main branch
- **Production Deployment**: Manual approval for releases
- **Database Migrations**: Automated migration execution
- **Health Checks**: Post-deployment validation
- **Rollback**: Automatic rollback on deployment failure

## Test Maintenance

### Adding New Tests
1. **Create Test File**: Follow naming convention `test_*.py`
2. **Add Markers**: Use appropriate pytest markers for categorization
3. **Include Factories**: Use existing factories or create new ones
4. **Mock Dependencies**: Mock external services and dependencies
5. **Test Edge Cases**: Include both happy path and error scenarios

### Test Review Checklist
- [ ] Tests follow AAA pattern (Arrange, Act, Assert)
- [ ] Appropriate use of fixtures and factories
- [ ] External dependencies are mocked
- [ ] Both success and failure scenarios are tested
- [ ] Test names are descriptive and clear
- [ ] Proper test markers are applied
- [ ] No test data leakage between tests
- [ ] Performance considerations addressed

### Common Patterns
```python
@pytest.mark.api
@pytest.mark.unit
class TestSSHEndpoints:
    """Test SSH API endpoints."""
    
    async def test_create_ssh_profile_success(self, async_client, auth_headers, test_user):
        """Test successful SSH profile creation."""
        # Arrange
        profile_data = {...}
        
        # Act
        response = await async_client.post("/api/ssh/profiles", json=profile_data, headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == test_user.id
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL is running
docker ps | grep postgres-test

# Restart PostgreSQL container
docker restart postgres-test

# Check connection
psql -h localhost -p 5433 -U test -d devpocket_test
```

#### Redis Connection Errors
```bash
# Check Redis is running
docker ps | grep redis-test

# Test Redis connection
redis-cli -h localhost -p 6380 ping
```

#### Test Failures
```bash
# Run with maximum verbosity
pytest -vvv --tb=long tests/failing_test.py

# Run single test with debugger
pytest --pdb tests/failing_test.py::test_function

# Show test output
pytest -s tests/failing_test.py
```

#### Coverage Issues
```bash
# Check which lines are missing coverage
pytest --cov=app --cov-report=term-missing

# Generate detailed HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Performance Issues
```bash
# Profile test execution time
pytest --durations=0 tests/

# Run performance tests only
pytest -m performance

# Memory profiling
pytest --memray tests/performance/
```

## Contributing

When contributing to the test suite:

1. **Follow Patterns**: Use existing test patterns and conventions
2. **Add Coverage**: Ensure new code includes comprehensive tests
3. **Update Documentation**: Update this file for significant changes
4. **Run Full Suite**: Execute complete test suite before submitting
5. **Check Coverage**: Verify coverage requirements are met

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)