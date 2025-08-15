# DevPocket Database Management

This document covers the comprehensive database management capabilities of the DevPocket API, including enhanced migration and seeding scripts, testing infrastructure, and best practices.

## Overview

The DevPocket API includes production-ready database management tools designed for development, testing, staging, and production environments. These tools provide:

- **Safe database migrations** with backup and rollback capabilities
- **Flexible data seeding** with factory-based test data generation
- **Comprehensive testing** with multiple test levels
- **Environment-specific configurations** for different deployment stages
- **Monitoring and statistics** for database health and performance

## Database Migration (`scripts/db_migrate.sh`)

The migration script provides enterprise-grade database schema management with safety features, automatic backups, and comprehensive error handling.

### Features

#### Safety and Validation
- **Migration target validation** - Ensures target revisions exist before execution
- **Data safety checks** - Analyzes potential data impact before migrations
- **Automatic backups** - Creates timestamped backups before major operations
- **Dry-run mode** - Preview changes without executing them
- **Confirmation prompts** - Interactive confirmation for dangerous operations

#### Environment Management
- **Multi-environment support** - Custom configuration for dev/staging/production
- **Environment file selection** - `--env-file` for different configurations
- **Virtual environment detection** - Automatic activation of Python environments
- **Database connectivity validation** - Connection testing before operations

#### Logging and Monitoring
- **Structured logging** - Timestamped, color-coded log messages
- **Operation tracking** - Complete audit trail of migration activities
- **Error reporting** - Detailed error messages with resolution guidance
- **Progress indicators** - Real-time feedback during long operations

### Usage Examples

#### Basic Operations
```bash
# Migrate to latest version
./scripts/db_migrate.sh

# Migrate to specific revision
./scripts/db_migrate.sh abc123def456

# Step migrations
./scripts/db_migrate.sh +1  # Forward one step
./scripts/db_migrate.sh -1  # Backward one step
```

#### Safety Features
```bash
# Preview changes without executing
./scripts/db_migrate.sh --dry-run head

# Force migration without prompts (CI/CD)
./scripts/db_migrate.sh --force head

# Skip backup creation (for development)
./scripts/db_migrate.sh --skip-backup head
```

#### Environment-Specific Operations
```bash
# Use custom environment file
./scripts/db_migrate.sh --env-file .env.production head

# Development environment
./scripts/db_migrate.sh --env-file .env.dev --skip-backup head

# Staging environment with dry-run
./scripts/db_migrate.sh --env-file .env.staging --dry-run head
```

#### Migration Management
```bash
# Generate new migration
./scripts/db_migrate.sh --generate "Add user preferences table"

# View migration history
./scripts/db_migrate.sh --history

# Check database connection only
./scripts/db_migrate.sh --check-only
```

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--dry-run` | Preview migrations without executing | `--dry-run head` |
| `--force` | Skip confirmation prompts | `--force head` |
| `--skip-backup` | Skip automatic backup creation | `--skip-backup head` |
| `--env-file FILE` | Use custom environment file | `--env-file .env.prod` |
| `--generate MSG` | Generate new migration | `--generate "Add indexes"` |
| `--history` | Show migration history | `--history` |
| `--check-only` | Check database connection only | `--check-only` |
| `-h, --help` | Show help message | `--help` |

### Migration Targets

| Target | Description | Example |
|--------|-------------|---------|
| `head` | Latest migration (default) | `./scripts/db_migrate.sh head` |
| `+1` | Forward one migration | `./scripts/db_migrate.sh +1` |
| `-1` | Backward one migration | `./scripts/db_migrate.sh -1` |
| `<revision>` | Specific revision ID | `./scripts/db_migrate.sh abc123` |

## Database Seeding (`scripts/db_seed.sh`)

The seeding script provides comprehensive test data generation with factory-based approach, conflict resolution, and advanced data management capabilities.

### Features

#### Data Generation
- **Factory-based seeding** - Uses test factories for realistic data
- **Multiple entity types** - Users, SSH profiles, commands, sessions, sync data
- **Configurable volumes** - From small test datasets to large performance datasets
- **Realistic relationships** - Proper foreign key relationships and dependencies
- **Randomized data** - Varied, realistic test data with temporal distribution

#### Data Management
- **Selective cleaning** - Clean specific entity types before seeding
- **Upsert operations** - Handle conflicts gracefully with PostgreSQL UPSERT
- **Database reset** - Complete database reset with schema rebuilding
- **Incremental seeding** - Add data without affecting existing records
- **Batch operations** - Efficient bulk operations for large datasets

#### Monitoring and Statistics
- **Real-time statistics** - Database table statistics and row counts
- **Performance monitoring** - Execution time and operation metrics
- **Data validation** - Verify data integrity after seeding
- **Progress reporting** - Real-time feedback during operations

### Entity Types

#### Users (`users`)
- User accounts with authentication data
- Multiple subscription tiers (free, pro, team)
- Realistic email addresses and usernames
- Creation dates distributed over time
- Active/inactive status variations

#### SSH Profiles (`ssh`)
- SSH connection profiles with realistic hostnames
- SSH keys with proper cryptographic fingerprints
- Authentication methods (password, key-based)
- Connection statistics and usage patterns
- Security configurations and options

#### Commands (`commands`)
- Command history with realistic shell commands
- Output data and error conditions
- Execution times and exit codes
- AI-suggested commands and explanations
- Working directory and environment context

#### Sessions (`sessions`)
- Terminal sessions with device information
- SSH connection details and parameters
- Session duration and activity patterns
- Multi-device session distribution
- Terminal configuration (rows, columns)

#### Sync Data (`sync`)
- Cross-device synchronization records
- Conflict resolution scenarios
- Version tracking and timestamps
- Device-specific metadata
- Data type categorization

### Usage Examples

#### Basic Seeding
```bash
# Seed all entity types (default: 10 records each)
./scripts/db_seed.sh

# Seed specific entity type
./scripts/db_seed.sh users 25
./scripts/db_seed.sh ssh 15
./scripts/db_seed.sh commands 100
```

#### Data Management
```bash
# Clean and reseed
./scripts/db_seed.sh --clean users 20

# Force clean without confirmation
./scripts/db_seed.sh --clean-force all 50

# Complete database reset
./scripts/db_seed.sh --reset-force
```

#### Conflict Resolution
```bash
# Use upsert for conflict handling
./scripts/db_seed.sh --upsert all 100

# Repeated seeding without conflicts
./scripts/db_seed.sh --upsert users 50
```

#### Statistics and Monitoring
```bash
# Show statistics after seeding
./scripts/db_seed.sh users 20 --stats

# Only show current statistics
./scripts/db_seed.sh --stats-only
```

#### Advanced Scenarios
```bash
# Development setup
./scripts/db_seed.sh --reset-force --upsert all 100 --stats

# Performance testing dataset
./scripts/db_seed.sh --clean-force --upsert all 10000

# Custom environment
./scripts/db_seed.sh --env-file .env.test users 25
```

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--clean` | Clean data before seeding (with confirmation) | `--clean users` |
| `--clean-force` | Force clean without confirmation | `--clean-force all` |
| `--reset` | Reset entire database (with confirmation) | `--reset` |
| `--reset-force` | Force reset without confirmation | `--reset-force` |
| `--upsert` | Use upsert for conflict resolution | `--upsert` |
| `--stats` | Show statistics after seeding | `--stats` |
| `--stats-only` | Only show statistics, don't seed | `--stats-only` |
| `--env-file FILE` | Use custom environment file | `--env-file .env.test` |
| `-h, --help` | Show help message | `--help` |

## Testing Infrastructure

The database management scripts include comprehensive testing with multiple test levels to ensure reliability and correctness.

### Test Categories

#### Unit Tests
- **Script function testing** - Individual function validation
- **Parameter validation** - Command line argument handling
- **Error condition testing** - Edge cases and error scenarios
- **Configuration testing** - Environment variable handling

#### Integration Tests
- **Database interaction testing** - Real database operations
- **Migration execution testing** - End-to-end migration scenarios
- **Seeding validation testing** - Data generation and verification
- **Cross-script communication** - Script interaction testing

#### End-to-End Tests
- **Complete workflow testing** - Full development workflows
- **Multi-environment testing** - Different environment configurations
- **Performance testing** - Large dataset handling
- **Recovery testing** - Backup and restore scenarios

#### Specific Test Files
- `test_db_migrate.py` - Migration script testing
- `test_db_seed.py` - Seeding script testing
- `test_db_integration.py` - Database integration testing
- `test_end_to_end.py` - Complete workflow testing
- `test_script_integration.py` - Cross-script testing

### Running Tests

#### All Tests
```bash
# Run all database script tests
pytest tests/test_scripts/

# Run with verbose output
pytest tests/test_scripts/ -v

# Run with coverage
pytest tests/test_scripts/ --cov=scripts
```

#### Specific Test Categories
```bash
# Migration tests only
pytest tests/test_scripts/test_db_migrate.py

# Seeding tests only
pytest tests/test_scripts/test_db_seed.py

# Integration tests
pytest tests/test_scripts/test_db_integration.py

# End-to-end tests
pytest tests/test_scripts/test_end_to_end.py
```

#### Test Environment Setup
```bash
# Setup test database
export DATABASE_URL="postgresql://test_user:test_pass@localhost/test_db"

# Run tests with custom environment
pytest tests/test_scripts/ --env-file .env.test

# Parallel test execution
pytest tests/test_scripts/ -n auto
```

## Environment Configuration

### Environment Variables

#### Database Connection
```bash
# Complete database URL (preferred)
DATABASE_URL="postgresql://user:password@host:port/database"

# Or individual components
DATABASE_HOST="localhost"
DATABASE_PORT="5432"
DATABASE_USER="devpocket_user"
DATABASE_PASSWORD="secure_password"
DATABASE_NAME="devpocket_warp_dev"
```

#### Script Configuration
```bash
# Debug mode
DB_DEBUG=1

# Backup directory
BACKUP_DIR="/path/to/backups"

# Maximum backup retention (days)
BACKUP_RETENTION_DAYS=30

# Default seeding counts
DEFAULT_SEED_COUNT=10
MAX_SEED_COUNT=10000
```

### Environment Files

#### Development (`.env.dev`)
```bash
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=devpocket_dev
DATABASE_PASSWORD=dev_password
DATABASE_NAME=devpocket_warp_dev
DB_DEBUG=1
BACKUP_DIR=./backups/dev
```

#### Testing (`.env.test`)
```bash
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_USER=devpocket_test
DATABASE_PASSWORD=test_password
DATABASE_NAME=devpocket_warp_test
DB_DEBUG=1
SKIP_BACKUP=true
```

#### Staging (`.env.staging`)
```bash
DATABASE_HOST=staging-db.example.com
DATABASE_PORT=5432
DATABASE_USER=devpocket_staging
DATABASE_PASSWORD=staging_secure_password
DATABASE_NAME=devpocket_warp_staging
BACKUP_DIR=/var/backups/staging
```

#### Production (`.env.production`)
```bash
DATABASE_HOST=prod-db.example.com
DATABASE_PORT=5432
DATABASE_USER=devpocket_prod
DATABASE_PASSWORD=prod_very_secure_password
DATABASE_NAME=devpocket_warp_prod
BACKUP_DIR=/var/backups/production
BACKUP_RETENTION_DAYS=90
```

## Best Practices

### Migration Best Practices

#### Pre-Migration Checklist
1. **Test in staging** - Always test migrations in staging environment first
2. **Review migration scripts** - Code review for all migration files
3. **Check dependencies** - Verify all required dependencies are available
4. **Backup verification** - Ensure backup process is working correctly
5. **Rollback plan** - Have a rollback strategy ready

#### Migration Execution
1. **Use dry-run first** - Always preview changes with `--dry-run`
2. **Monitor logs** - Watch for warnings and errors during execution
3. **Verify results** - Check database state after migrations
4. **Document changes** - Update documentation for schema changes
5. **Communicate changes** - Notify team of database changes

#### Production Migrations
```bash
# Production migration workflow
./scripts/db_migrate.sh --env-file .env.production --dry-run head
./scripts/db_migrate.sh --env-file .env.production head
```

### Seeding Best Practices

#### Development Seeding
1. **Use appropriate volumes** - Don't over-seed development databases
2. **Maintain consistency** - Use consistent seeding patterns across team
3. **Regular cleanup** - Periodically clean and reseed development data
4. **Test scenarios** - Create specific scenarios for testing features
5. **Document test users** - Keep track of test accounts and credentials

#### Performance Testing
```bash
# Performance testing dataset
./scripts/db_seed.sh --clean-force --upsert all 10000 --stats
```

#### CI/CD Integration
```bash
# Automated testing pipeline
./scripts/db_seed.sh --reset-force --upsert all 100
pytest tests/
./scripts/db_seed.sh --stats-only
```

### Security Best Practices

#### Credential Management
1. **Environment-specific files** - Use separate credential files per environment
2. **Secure storage** - Store production credentials securely (e.g., HashiCorp Vault)
3. **Least privilege** - Grant minimum required permissions to database users
4. **Regular rotation** - Rotate database passwords regularly
5. **Access logging** - Log all database access for audit trails

#### Backup Security
1. **Encrypted backups** - Encrypt backup files at rest
2. **Secure transfer** - Use secure protocols for backup transfer
3. **Access control** - Restrict backup file access to authorized personnel
4. **Retention policies** - Follow data retention and deletion policies
5. **Test restores** - Regularly test backup restore procedures

## Troubleshooting

### Common Issues

#### Migration Failures

**Connection Issues**
```bash
# Check database connectivity
./scripts/db_migrate.sh --check-only

# Test with different environment file
./scripts/db_migrate.sh --env-file .env.test --check-only
```

**Permission Errors**
```bash
# Error: permission denied for schema migrations
# Solution: Grant schema permissions to user
GRANT CREATE, USAGE ON SCHEMA public TO devpocket_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO devpocket_user;
```

**Lock Timeouts**
```bash
# Error: could not obtain lock on relation
# Solution: Check for long-running transactions
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

#### Seeding Issues

**Foreign Key Violations**
```bash
# Clean in dependency order
./scripts/db_seed.sh --clean-force commands
./scripts/db_seed.sh --clean-force sessions  
./scripts/db_seed.sh --clean-force users
```

**Duplicate Data Errors**
```bash
# Use upsert mode for conflict resolution
./scripts/db_seed.sh --upsert users 50
```

**Memory Issues**
```bash
# Reduce batch sizes for large datasets
./scripts/db_seed.sh users 1000  # Instead of 10000
```

#### Performance Issues

**Slow Migrations**
```bash
# Check for missing indexes during migration
# Monitor with:
SELECT * FROM pg_stat_progress_create_index;
```

**Slow Seeding**
```bash
# Disable indexes temporarily for bulk inserts
# Re-enable after seeding completes
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Enable debug mode
export DB_DEBUG=1

# Run with verbose output
./scripts/db_migrate.sh --dry-run head
./scripts/db_seed.sh --stats-only
```

### Log Analysis

#### Migration Logs
- **Backup creation logs** - Verify backup file creation and size
- **Migration execution logs** - Check for warnings and errors
- **Verification logs** - Confirm target revision reached
- **Performance metrics** - Monitor execution time and resource usage

#### Seeding Logs
- **Data generation logs** - Verify record creation counts
- **Relationship logs** - Check foreign key relationships
- **Conflict resolution logs** - Monitor upsert operations
- **Statistics logs** - Validate final database state

## API Integration

The database management scripts can be integrated with the DevPocket API for programmatic access.

### Database Management Endpoints

#### Migration Status
```http
GET /api/admin/database/status
Authorization: Bearer <token>
```

#### Run Migrations
```http
POST /api/admin/database/migrate
Authorization: Bearer <token>
Content-Type: application/json

{
  "target": "head",
  "dry_run": false,
  "skip_backup": false,
  "force": false
}
```

#### Seed Database
```http
POST /api/admin/database/seed
Authorization: Bearer <token>
Content-Type: application/json

{
  "seed_type": "all",
  "count": 100,
  "clean_first": false,
  "use_upsert": true,
  "environment": "development"
}
```

#### Database Statistics
```http
GET /api/admin/database/stats
Authorization: Bearer <token>
```

### Development Utilities

#### Generate Test Data
```http
POST /api/dev/test-data/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "scenario": "user_onboarding",
  "parameters": {
    "user_count": 10,
    "ssh_profiles_per_user": 3
  }
}
```

#### Cleanup Test Data
```http
POST /api/dev/cleanup
Authorization: Bearer <token>
Content-Type: application/json

{
  "older_than_hours": 24,
  "include_test_users": true,
  "data_types": ["commands", "sessions"]
}
```

## Monitoring and Alerting

### Database Health Monitoring

#### Key Metrics
- **Migration status** - Current vs target revision
- **Data volume** - Row counts per table
- **Performance metrics** - Query execution times
- **Connection health** - Active connections and pool status
- **Backup status** - Backup creation and retention

#### Alerting Rules
```yaml
# Example alerting configuration
migration_behind:
  condition: pending_migrations > 0
  severity: warning
  message: "Database migrations are behind target"

backup_failed:
  condition: last_backup_age > 24h
  severity: critical
  message: "Database backup has not completed in 24 hours"

seeding_failed:
  condition: seeding_error_rate > 0.1
  severity: warning
  message: "High error rate in database seeding operations"
```

### Performance Monitoring

#### Query Performance
```sql
-- Monitor slow queries
SELECT query, mean_exec_time, calls, total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC;
```

#### Table Statistics
```sql
-- Monitor table growth
SELECT 
  schemaname,
  relname,
  n_live_tup,
  n_dead_tup,
  last_autovacuum,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

This comprehensive database management system provides enterprise-grade capabilities for managing the DevPocket API database across all environments, from development to production.