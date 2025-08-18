# DevPocket Test Environment - Quick Start Guide

## 🚀 Quick Setup & Run

### 1. Start Test Environment
```bash
./scripts/setup_test_env.sh
```

### 2. Run All Tests
```bash
# Using Docker (recommended)
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/ -v

# Using local script (if Python dependencies installed locally)
./scripts/run_tests_local.sh
```

### 3. Teardown When Done
```bash
docker compose -f docker-compose.test.yaml down -v
```

## 🎯 Common Test Commands

### Run Specific Test Categories
```bash
# Database tests
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/test_database/ -v

# Authentication tests
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/test_auth/ -v

# API tests
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/test_api/ -v

# Run with coverage
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/ --cov=app --cov-report=html
```

### Run Individual Test Files
```bash
# Specific test file
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/test_auth/test_security.py -v

# Specific test function
docker compose -f docker-compose.test.yaml run --rm test-runner python -m pytest tests/test_auth/test_security.py::TestJWTTokens::test_create_access_token -v
```

## 🔧 Troubleshooting

### Reset Test Database
```bash
docker compose -f docker-compose.test.yaml run --rm test-runner python scripts/init_test_db.py
```

### Check Database Connectivity
```bash
# PostgreSQL
docker compose -f docker-compose.test.yaml exec postgres-test psql -U test -d devpocket_test -c "SELECT 1;"

# Redis
docker compose -f docker-compose.test.yaml exec redis-test redis-cli ping
```

### View Container Logs
```bash
# All services
docker compose -f docker-compose.test.yaml logs

# Specific service
docker compose -f docker-compose.test.yaml logs postgres-test
docker compose -f docker-compose.test.yaml logs redis-test
```

## 📊 Test Infrastructure Status

### Services Running
- ✅ PostgreSQL Test DB: `localhost:5433`
- ✅ Redis Test Cache: `localhost:6380`  
- ✅ Test Runner Container: Ready

### Test Coverage Areas
- ✅ Unit Tests: Models, Services, Utilities
- ✅ Database Tests: Repositories, Models
- ✅ Authentication Tests: JWT, Password Security
- ✅ API Tests: Endpoints, Validation
- ✅ Integration Tests: End-to-end workflows

### Environment Variables (Auto-configured)
```bash
ENVIRONMENT=test
TESTING=true
DATABASE_URL=postgresql://test:test@localhost:5433/devpocket_test
REDIS_URL=redis://localhost:6380
JWT_SECRET_KEY=test_secret_key_for_testing_only
```

## ⚡ Performance Tips

1. **Keep containers running** between test runs for faster execution
2. **Use specific test paths** instead of running all tests during development
3. **Parallel execution** available with `pytest-xdist` plugin
4. **Coverage reports** generated in `htmlcov/index.html`

## 🎯 Next Steps

With Phase 1 complete, you can now:
- Run comprehensive test suites reliably
- Develop new features with proper test coverage
- Debug database-related issues in isolation
- Implement Phase 2 (API and Integration tests)

---

**Need help?** Check `PHASE1_IMPLEMENTATION_SUMMARY.md` for detailed implementation notes.