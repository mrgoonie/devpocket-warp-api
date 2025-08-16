#!/bin/bash

# DevPocket Local Test Runner Script
# Runs tests using the local test environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "🧪 Running DevPocket tests locally..."

# Check if test environment is running
if ! docker compose -f docker-compose.test.yaml ps postgres-test | grep -q "Up"; then
    print_error "Test environment is not running. Please run:"
    echo "  ./scripts/setup_test_env.sh"
    exit 1
fi

# Set test environment variables
export ENVIRONMENT=test
export TESTING=true
export DATABASE_URL=postgresql://test:test@localhost:5433/devpocket_test
export REDIS_URL=redis://localhost:6380
export JWT_SECRET_KEY=test_secret_key_for_testing_only
export JWT_ALGORITHM=HS256
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
export OPENROUTER_API_BASE_URL=http://localhost:8001/mock
export LOG_LEVEL=INFO
export PYTHONPATH=/home/dev/www/devpocket-warp-api

# Create test reports directory
mkdir -p test-reports htmlcov

print_status "Environment variables set for testing"

# Run tests with the specified arguments or default options
if [ $# -eq 0 ]; then
    print_status "Running all tests with coverage..."
    python3 -m pytest tests/ \
        --tb=short \
        --verbose \
        --cov=app \
        --cov-report=html:htmlcov \
        --cov-report=xml:test-reports/coverage.xml \
        --cov-report=term-missing \
        --junit-xml=test-reports/junit.xml \
        --durations=10 \
        --timeout=300
else
    print_status "Running tests with custom arguments: $*"
    python3 -m pytest "$@"
fi

exit_code=$?

if [ $exit_code -eq 0 ]; then
    print_success "🎉 All tests passed!"
    if [ -d "htmlcov" ]; then
        print_status "Coverage report generated in htmlcov/index.html"
    fi
else
    print_error "❌ Some tests failed (exit code: $exit_code)"
fi

exit $exit_code