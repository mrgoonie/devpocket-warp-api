#!/bin/bash

# DevPocket Test Environment Setup Script
# This script sets up the test databases and runs migrations

set -e  # Exit on any error

echo "🧪 Setting up DevPocket test environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker is running ✓"

# Stop any existing test containers
print_status "Stopping existing test containers..."
docker compose -f docker-compose.test.yaml down -v --remove-orphans 2>/dev/null || true

# Build and start test infrastructure
print_status "Building and starting test infrastructure..."
docker compose -f docker-compose.test.yaml up -d postgres-test redis-test

# Wait for services to be healthy
print_status "Waiting for PostgreSQL test database to be ready..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker compose -f docker-compose.test.yaml exec -T postgres-test pg_isready -U test -d devpocket_test >/dev/null 2>&1; then
        print_success "PostgreSQL test database is ready!"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    print_error "PostgreSQL test database failed to start within $timeout seconds"
    docker compose -f docker-compose.test.yaml logs postgres-test
    exit 1
fi

print_status "Waiting for Redis test instance to be ready..."
timeout=30
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker compose -f docker-compose.test.yaml exec -T redis-test redis-cli ping >/dev/null 2>&1; then
        print_success "Redis test instance is ready!"
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ $elapsed -ge $timeout ]; then
    print_error "Redis test instance failed to start within $timeout seconds"
    docker compose -f docker-compose.test.yaml logs redis-test
    exit 1
fi

# Set environment variables for testing
export ENVIRONMENT=test
export TESTING=true
export DATABASE_URL=postgresql://test:test@localhost:5433/devpocket_test
export REDIS_URL=redis://localhost:6380
export JWT_SECRET_KEY=test_secret_key_for_testing_only

print_status "Environment variables set for testing"

# Check database connectivity
print_status "Testing database connectivity..."
if python3 -c "
import asyncio
import asyncpg

async def test_connection():
    try:
        conn = await asyncpg.connect('postgresql://test:test@localhost:5433/devpocket_test')
        await conn.execute('SELECT 1')
        await conn.close()
        print('✓ Database connection successful')
        return True
    except Exception as e:
        print(f'✗ Database connection failed: {e}')
        return False

result = asyncio.run(test_connection())
exit(0 if result else 1)
"; then
    print_success "Database connectivity test passed!"
else
    print_error "Database connectivity test failed"
    exit 1
fi

# Run Alembic migrations on test database
print_status "Running Alembic migrations on test database..."
if python3 -c "
import os
import sys
sys.path.insert(0, '.')

# Set test environment
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5433/devpocket_test'
os.environ['ENVIRONMENT'] = 'test'

from alembic.config import Config
from alembic import command

# Create Alembic config
alembic_cfg = Config('alembic.ini')
alembic_cfg.set_main_option('sqlalchemy.url', 'postgresql://test:test@localhost:5433/devpocket_test')

try:
    # Run migrations
    command.upgrade(alembic_cfg, 'head')
    print('✓ Alembic migrations completed successfully')
except Exception as e:
    print(f'✗ Alembic migrations failed: {e}')
    sys.exit(1)
"; then
    print_success "Database migrations completed!"
else
    print_error "Database migrations failed"
    exit 1
fi

# Test Redis connectivity
print_status "Testing Redis connectivity..."
if python3 -c "
import asyncio
import redis.asyncio as aioredis

async def test_redis():
    try:
        redis_client = await aioredis.from_url('redis://localhost:6380')
        await redis_client.ping()
        await redis_client.close()
        print('✓ Redis connection successful')
        return True
    except Exception as e:
        print(f'✗ Redis connection failed: {e}')
        return False

result = asyncio.run(test_redis())
exit(0 if result else 1)
"; then
    print_success "Redis connectivity test passed!"
else
    print_error "Redis connectivity test failed"
    exit 1
fi

print_success "🎉 Test environment setup completed successfully!"
print_status "Test infrastructure is ready:"
print_status "  • PostgreSQL Test DB: postgresql://test:test@localhost:5433/devpocket_test"
print_status "  • Redis Test Instance: redis://localhost:6380"
print_status ""
print_status "You can now run tests with:"
print_status "  python -m pytest tests/ --tb=short -v"
print_status ""
print_status "To tear down the test environment:"
print_status "  docker compose -f docker-compose.test.yaml down -v"