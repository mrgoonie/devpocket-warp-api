# DevPocket API Scripts

This directory contains utility scripts for the DevPocket API development and deployment.

## Available Scripts

### Development Script (`dev.py`)

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

### Database Utilities (`db_utils.py`)

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

1. **Initial Setup**:
   ```bash
   # Create environment file
   python scripts/dev.py env
   
   # Install dependencies
   python scripts/dev.py install
   ```

2. **Database Setup** (requires PostgreSQL running):
   ```bash
   # Full database setup
   python scripts/dev.py db
   
   # Or step by step:
   python scripts/dev.py db-create
   python scripts/dev.py migrate
   ```

3. **Development**:
   ```bash
   # Start server
   python scripts/dev.py start
   
   # Run quality checks before commit
   python scripts/dev.py check
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

## Error Handling

All scripts include comprehensive error handling and logging. Check the logs for detailed error information if operations fail.