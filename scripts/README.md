# DevPocket API Scripts

This directory contains utility scripts for the DevPocket API development and deployment.

## Available Scripts

### Shell Scripts (Recommended)

Production-ready shell scripts with comprehensive error handling and logging:

#### Database Migration (`db_migrate.sh`)
Run Alembic migrations with proper error handling:
```bash
./scripts/db_migrate.sh                # Migrate to latest
./scripts/db_migrate.sh head           # Migrate to latest
./scripts/db_migrate.sh +1             # Migrate one step forward
./scripts/db_migrate.sh -1             # Migrate one step backward
./scripts/db_migrate.sh abc123         # Migrate to specific revision
./scripts/db_migrate.sh -g "Add users" # Generate new migration
./scripts/db_migrate.sh --history      # Show migration history
./scripts/db_migrate.sh --check-only   # Check DB connection only
```

#### Database Seeding (`db_seed.sh`)
Seed database with sample data using existing factories:
```bash
./scripts/db_seed.sh                   # Seed all types (10 records each)
./scripts/db_seed.sh users 25          # Create 25 sample users
./scripts/db_seed.sh ssh 15            # Create 15 SSH connections
./scripts/db_seed.sh all 5             # Create 5 records of each type
./scripts/db_seed.sh --stats-only      # Show database statistics only
./scripts/db_seed.sh commands 20 --stats # Create 20 commands and show stats
```

#### Database Reset (`db_reset.sh`)
Complete database reset (drop, create, migrate, seed):
```bash
./scripts/db_reset.sh                  # Reset with confirmation and seeding
./scripts/db_reset.sh -f               # Reset without confirmation
./scripts/db_reset.sh --no-seed        # Reset without seeding
./scripts/db_reset.sh --seed-type users # Reset and seed users only
./scripts/db_reset.sh -f --seed-count 25 # Reset and create 25 seed records
```

#### Test Runner (`run_tests.sh`)
Run pytest with coverage and comprehensive reporting:
```bash
./scripts/run_tests.sh                 # Run all tests with coverage
./scripts/run_tests.sh -t unit         # Run unit tests only
./scripts/run_tests.sh -p -v           # Run in parallel with verbose output
./scripts/run_tests.sh -m "not slow"   # Run tests excluding slow ones
./scripts/run_tests.sh tests/test_auth/ # Run tests in specific directory
./scripts/run_tests.sh --clean -t api  # Clean artifacts and run API tests
./scripts/run_tests.sh --no-cov -q     # Run tests without coverage, quietly
./scripts/run_tests.sh --summary-only  # Show test structure summary
```

#### Code Formatting (`format_code.sh`)
Run black, ruff, mypy with proper exit codes:
```bash
./scripts/format_code.sh               # Format entire app/ directory
./scripts/format_code.sh app/core/     # Format specific directory
./scripts/format_code.sh main.py       # Format specific file
./scripts/format_code.sh -c            # Check formatting without changes
./scripts/format_code.sh -f            # Fix all auto-fixable issues
./scripts/format_code.sh --black-only  # Run only Black formatter
./scripts/format_code.sh --strict      # Use strict type checking
./scripts/format_code.sh --report      # Generate detailed quality report
./scripts/format_code.sh --stats-only  # Show code statistics only
```

### Python Scripts (Legacy)

#### Development Script (`dev.py`)
Main development utility script for common tasks:
```bash
# Start development server
python scripts/dev.py start

# Install dependencies
python scripts/dev.py install

# Code quality checks
python scripts/dev.py format    # Format with black
python scripts/dev.py lint      # Lint with ruff
python scripts/dev.py typecheck # Type check with mypy
python scripts/dev.py test      # Run tests
python scripts/dev.py check     # Run all checks

# Database operations
python scripts/dev.py db        # Full database setup
python scripts/dev.py db-create # Create database
python scripts/dev.py migrate   # Run migrations
python scripts/dev.py migration # Create new migration

# Utilities
python scripts/dev.py env       # Create .env from template
python scripts/dev.py clean     # Clean generated files
```

#### Database Utilities (`db_utils.py`)
Database-specific operations:
```bash
# Database management
python scripts/db_utils.py create  # Create database
python scripts/db_utils.py drop    # Drop database
python scripts/db_utils.py init    # Initialize tables
python scripts/db_utils.py reset   # Reset database
python scripts/db_utils.py health  # Health check
python scripts/db_utils.py test    # Test connection
```

## Setup Process

### Quick Start (Recommended)

1. **Initial Setup**:
   ```bash
   # Run main setup script (creates venv, installs deps, sets up .env)
   python setup.py
   
   # Or manually:
   python scripts/dev.py env      # Create environment file
   python scripts/dev.py install # Install dependencies
   ```

2. **Database Setup** (requires PostgreSQL running):
   ```bash
   # Complete database reset and setup
   ./scripts/db_reset.sh -f
   
   # Or step by step:
   ./scripts/db_migrate.sh        # Run migrations
   ./scripts/db_seed.sh           # Seed with sample data
   ```

3. **Development Workflow**:
   ```bash
   # Start development server
   python scripts/dev.py start
   # OR
   uvicorn main:app --reload
   
   # Run tests before commit
   ./scripts/run_tests.sh
   
   # Format and check code quality
   ./scripts/format_code.sh
   ```

### Advanced Usage

4. **Testing**:
   ```bash
   # Run specific test types
   ./scripts/run_tests.sh -t unit     # Unit tests only
   ./scripts/run_tests.sh -t api      # API tests only
   ./scripts/run_tests.sh -p          # Parallel execution
   
   # Generate test reports
   ./scripts/run_tests.sh --clean     # Clean and run all tests
   ```

5. **Database Management**:
   ```bash
   # Reset development database
   ./scripts/db_reset.sh --seed-type users --seed-count 50
   
   # Create migration for schema changes
   ./scripts/db_migrate.sh -g "Add new table"
   
   # Seed specific data types
   ./scripts/db_seed.sh ssh 25        # 25 SSH connections
   ```

6. **Code Quality**:
   ```bash
   # Check code quality (no changes)
   ./scripts/format_code.sh -c
   
   # Auto-fix issues
   ./scripts/format_code.sh -f
   
   # Generate quality report
   ./scripts/format_code.sh --report
   ```

## Database Schema

The database layer includes:

### Models
- **User**: User accounts with authentication and subscription info
- **UserSettings**: User preferences and configuration
- **Session**: Terminal sessions with device tracking
- **Command**: Executed commands with metadata and results
- **SSHProfile**: SSH connection profiles
- **SSHKey**: SSH keys for authentication
- **SyncData**: Cross-device synchronization data

### Repository Pattern
Each model has a corresponding repository class providing:
- CRUD operations
- Specialized queries
- Business logic methods
- Bulk operations
- Statistics and analytics

### Features
- UUID primary keys
- Automatic timestamps (created_at, updated_at)
- Soft deletes where appropriate
- Optimized indexes for common queries
- Foreign key constraints with CASCADE deletes
- JSON fields for flexible data storage

## Migration Management

Using Alembic for database migrations:

```bash
# Create new migration
python scripts/dev.py migration

# Apply migrations
python scripts/dev.py migrate

# Check migration status
alembic current

# View migration history
alembic history --verbose
```

## Environment Configuration

Required environment variables (see `.env.example`):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: JWT signing key
- Plus additional configuration for app settings

## Script Features

### Error Handling & Logging
- **Comprehensive Error Handling**: All shell scripts include proper error trapping and exit codes
- **Colored Logging**: Timestamped log messages with color-coded severity levels (INFO, WARN, ERROR, SUCCESS)
- **Graceful Failures**: Scripts fail fast with clear error messages and suggestions for resolution
- **Exit Code Standards**: Consistent exit codes for CI/CD integration

### Shell Script Advantages
- **Production Ready**: Robust error handling and logging suitable for production use
- **Self-Contained**: No Python import dependencies, work in any environment
- **Fast Execution**: Direct shell execution without Python startup overhead
- **CI/CD Friendly**: Clear exit codes and structured output for automation
- **User Friendly**: Comprehensive help messages and usage examples

### Environment Integration
- **Virtual Environment Detection**: Automatically activates venv if available
- **Configuration Validation**: Checks for required tools and dependencies
- **Environment Variables**: Supports both .env files and direct environment variables
- **Cross-Platform**: Works on Linux, macOS, and WSL

### Development Workflow Integration
```bash
# Typical development workflow
./scripts/format_code.sh -c        # Check code quality
./scripts/run_tests.sh -t unit     # Run unit tests
./scripts/db_migrate.sh            # Apply any new migrations
./scripts/run_tests.sh             # Run full test suite
git add . && git commit -m "..."   # Commit changes
```

### CI/CD Integration
The shell scripts are designed for easy integration with CI/CD pipelines:
```bash
# Example CI pipeline steps
./scripts/format_code.sh --check   # Fail if formatting issues
./scripts/run_tests.sh --no-db-check  # Run tests without DB dependency
./scripts/db_reset.sh -f --no-seed    # Reset test database
```

## Error Handling

All scripts include comprehensive error handling and logging:
- **Error Trapping**: `set -euo pipefail` for strict error handling
- **Line Number Reporting**: Failed commands report exact line numbers
- **Cleanup on Exit**: Temporary files are cleaned up even on script failure
- **Detailed Error Messages**: Clear explanations of what went wrong and how to fix it
- **Dependency Checking**: Validates required tools and services before execution