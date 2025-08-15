# Shell Script Test Suite

This directory contains comprehensive tests for all shell scripts in the `scripts/` directory.

## Test Structure

### Test Files

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`test_db_migrate.py`** - Tests for `db_migrate.sh` script
- **`test_db_seed.py`** - Tests for `db_seed.sh` script  
- **`test_db_reset.py`** - Tests for `db_reset.sh` script
- **`test_run_tests.py`** - Tests for `run_tests.sh` script
- **`test_format_code.py`** - Tests for `format_code.sh` script
- **`test_script_integration.py`** - Integration tests across scripts
- **`test_script_verification.py`** - Infrastructure verification tests
- **`test_runner.py`** - Simple test runner (works without pytest)

### Scripts Tested

1. **`db_migrate.sh`** - Database migration script using Alembic
2. **`db_seed.sh`** - Database seeding script with factory data
3. **`db_reset.sh`** - Complete database reset workflow
4. **`run_tests.sh`** - Test runner with coverage and reporting
5. **`format_code.sh`** - Code formatting and quality checks

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Script syntax validation
- Argument parsing
- Help system functionality
- Error handling
- Tool dependency checking

### Integration Tests (`@pytest.mark.integration`)
- Script interactions
- End-to-end workflows
- Database integration
- Tool integration (Alembic, pytest, Black, Ruff, MyPy)

### Database Tests (`@pytest.mark.database`) 
- Database connection handling
- Migration operations
- Seeding workflows
- Reset procedures

## Test Coverage

### Functionality Tested

✅ **Script Existence & Permissions**
- All scripts exist and are executable
- Proper file permissions (755)
- Valid bash syntax

✅ **Help & Documentation**
- `--help` and `-h` options work
- Complete usage information
- Examples and environment docs

✅ **Argument Parsing**
- Valid argument combinations
- Invalid argument rejection
- Option validation
- Default value handling

✅ **Error Handling**
- Graceful failure modes
- Meaningful error messages
- Proper exit codes
- Timeout handling

✅ **Tool Integration**
- Alembic integration (migrations)
- Pytest integration (testing)
- Black/Ruff/MyPy integration (formatting)
- Virtual environment support

✅ **Environment Handling**
- Environment variable usage
- Virtual environment activation
- Working directory management
- CI/CD compatibility

✅ **Workflow Testing**
- Database reset sequence
- Migration + seeding workflows
- Test + format workflows
- Error recovery scenarios

### Test Features

- **Comprehensive Mocking** - External dependencies properly mocked
- **Fixtures** - Reusable test infrastructure
- **Parametrized Tests** - Testing multiple scenarios efficiently
- **Performance Testing** - Scripts complete within reasonable time
- **Security Testing** - Safe handling of user input
- **Compatibility Testing** - Works across different environments

## Running Tests

### With Pytest (Recommended)

```bash
# Run all script tests
pytest tests/test_scripts/ -v

# Run specific test categories
pytest tests/test_scripts/ -m unit
pytest tests/test_scripts/ -m integration
pytest tests/test_scripts/ -m database

# Run tests for specific script
pytest tests/test_scripts/test_db_migrate.py -v

# Run with coverage
pytest tests/test_scripts/ --cov=scripts --cov-report=html
```

### With Simple Test Runner

```bash
# Run basic verification tests
python tests/test_scripts/test_runner.py
```

### Manual Testing

```bash
# Test script syntax
for script in scripts/*.sh; do bash -n "$script" && echo "✅ $script"; done

# Test help commands  
for script in scripts/*.sh; do "$script" --help >/dev/null && echo "✅ $script"; done

# Test invalid arguments
for script in scripts/*.sh; do "$script" --invalid >/dev/null 2>&1 || echo "✅ $script"; done
```

## Test Configuration

### Environment Variables

Tests use these environment variables:

```bash
ENVIRONMENT=test
TESTING=true
DATABASE_URL=postgresql://test:test@localhost:5433/devpocket_test
REDIS_URL=redis://localhost:6380
PROJECT_ROOT=/path/to/devpocket-warp-api
```

### Pytest Markers

- `unit` - Unit tests
- `integration` - Integration tests
- `database` - Database-related tests
- `slow` - Tests that take longer to run
- `external` - Tests requiring external services

### Mock Strategy

Tests extensively use mocking to:
- Isolate script logic from external dependencies
- Simulate various success/failure scenarios
- Test error handling paths
- Ensure fast test execution

## Continuous Integration

### GitHub Actions

```yaml
name: Script Tests
on: [push, pull_request]
jobs:
  test-scripts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Test shell scripts
        run: pytest tests/test_scripts/ -v
```

### Pre-commit Hooks

```yaml
repos:
  - repo: local
    hooks:
      - id: test-scripts
        name: Test Shell Scripts
        entry: pytest tests/test_scripts/ -x
        language: system
        pass_filenames: false
```

## Best Practices

### Test Writing Guidelines

1. **Test Behavior, Not Implementation** - Focus on what scripts do, not how
2. **Use Descriptive Names** - Test names should explain what's being tested
3. **Mock External Dependencies** - Don't rely on real databases, network, etc.
4. **Test Error Cases** - Ensure scripts handle failures gracefully
5. **Keep Tests Fast** - Use timeouts and avoid unnecessary delays
6. **Test Edge Cases** - Invalid inputs, missing files, permission issues

### Script Development Guidelines

1. **Consistent Logging** - Use standard log levels and formats
2. **Proper Exit Codes** - Return appropriate exit codes for success/failure
3. **Help Documentation** - Provide comprehensive help text
4. **Input Validation** - Validate all user inputs
5. **Error Handling** - Handle and report errors meaningfully
6. **Environment Awareness** - Work in different environments (dev, CI, prod)

## Troubleshooting

### Common Issues

**Tests fail with "Command not found"**
- Ensure tools are installed: `pip install -r requirements.txt`
- Check PATH includes tool locations
- Verify virtual environment activation

**Database connection errors**
- Check `DATABASE_URL` environment variable
- Ensure test database is running
- Verify database permissions

**Permission denied errors**
- Check script permissions: `chmod +x scripts/*.sh`
- Verify user has execute permissions
- Check directory permissions

**Timeout errors**
- Scripts may be waiting for input
- Check for interactive prompts
- Increase timeout values in tests

### Debug Mode

Run tests with debug output:

```bash
# Pytest debug mode
pytest tests/test_scripts/ -v -s --tb=long

# Script debug mode
bash -x scripts/script_name.sh --help
```

## Contributing

When adding new scripts or modifying existing ones:

1. **Add corresponding tests** in `tests/test_scripts/`
2. **Follow test naming conventions** - `test_*.py` files, `test_*` functions
3. **Include all test categories** - unit, integration, error cases
4. **Update this README** if adding new test patterns
5. **Ensure all tests pass** before submitting PR

### Test Checklist

- [ ] Script syntax is valid (`bash -n script.sh`)
- [ ] Help command works (`script.sh --help`)
- [ ] Invalid arguments are rejected properly
- [ ] Environment variables are respected
- [ ] Error cases are handled gracefully
- [ ] Exit codes are appropriate
- [ ] Tests are added for new functionality
- [ ] Tests pass in CI environment