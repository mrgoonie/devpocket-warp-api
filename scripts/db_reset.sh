#!/bin/bash
# DevPocket API - Database Reset Script  
# Resets database completely (drop, create, migrate, seed)

set -euo pipefail

# Color definitions for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Script directory and project root
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "[${timestamp}] ${BLUE}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "[${timestamp}] ${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "[${timestamp}] ${RED}[ERROR]${NC} $message" >&2
            ;;
        "SUCCESS")
            echo -e "[${timestamp}] ${GREEN}[SUCCESS]${NC} $message"
            ;;
    esac
}

# Check if virtual environment exists and activate it
activate_venv() {
    local venv_path="${PROJECT_ROOT}/venv"
    
    if [[ -d "$venv_path" ]]; then
        log "INFO" "Activating virtual environment..."
        source "$venv_path/bin/activate"
        log "SUCCESS" "Virtual environment activated"
    else
        log "WARN" "Virtual environment not found at $venv_path"
        log "INFO" "Using system Python environment"
    fi
}

# Confirm destructive operation
confirm_reset() {
    local force="$1"
    
    if [[ "$force" != true ]]; then
        echo
        log "WARN" "This will completely reset the database!"
        log "WARN" "All existing data will be permanently lost."
        echo
        read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
        
        if [[ "$confirmation" != "yes" ]]; then
            log "INFO" "Database reset cancelled by user"
            exit 0
        fi
    fi
    
    log "INFO" "Proceeding with database reset..."
}

# Check if database utilities are available
check_requirements() {
    log "INFO" "Checking requirements..."
    
    # Check if db_utils.py exists
    if [[ ! -f "${SCRIPT_DIR}/db_utils.py" ]]; then
        log "ERROR" "Database utilities not found: ${SCRIPT_DIR}/db_utils.py"
        exit 1
    fi
    
    # Check if migration script exists
    if [[ ! -f "${SCRIPT_DIR}/db_migrate.sh" ]]; then
        log "ERROR" "Migration script not found: ${SCRIPT_DIR}/db_migrate.sh"
        exit 1
    fi
    
    # Check if seed script exists
    if [[ ! -f "${SCRIPT_DIR}/db_seed.sh" ]]; then
        log "WARN" "Seed script not found: ${SCRIPT_DIR}/db_seed.sh"
        log "INFO" "Database will be reset without seeding"
    fi
    
    log "SUCCESS" "Requirements check passed"
}

# Reset database using db_utils.py
reset_database() {
    log "INFO" "Resetting database (drop, create, initialize)..."
    
    cd "$PROJECT_ROOT"
    
    if python "${SCRIPT_DIR}/db_utils.py" reset; then
        log "SUCCESS" "Database reset completed"
    else
        log "ERROR" "Database reset failed"
        exit 1
    fi
}

# Run database migrations
run_migrations() {
    log "INFO" "Running database migrations..."
    
    # Make migration script executable if needed
    chmod +x "${SCRIPT_DIR}/db_migrate.sh"
    
    if "${SCRIPT_DIR}/db_migrate.sh"; then
        log "SUCCESS" "Database migrations completed"
    else
        log "ERROR" "Database migrations failed"
        exit 1
    fi
}

# Seed database with sample data
seed_database() {
    local seed_type="$1"
    local seed_count="$2"
    local skip_seed="$3"
    
    if [[ "$skip_seed" == true ]]; then
        log "INFO" "Skipping database seeding"
        return 0
    fi
    
    if [[ ! -f "${SCRIPT_DIR}/db_seed.sh" ]]; then
        log "WARN" "Seed script not available, skipping seeding"
        return 0
    fi
    
    log "INFO" "Seeding database with sample data..."
    
    # Make seed script executable if needed
    chmod +x "${SCRIPT_DIR}/db_seed.sh"
    
    if "${SCRIPT_DIR}/db_seed.sh" "$seed_type" "$seed_count"; then
        log "SUCCESS" "Database seeding completed"
    else
        log "WARN" "Database seeding failed, but continuing..."
    fi
}

# Verify database health after reset
verify_database() {
    log "INFO" "Verifying database health..."
    
    cd "$PROJECT_ROOT"
    
    # Use db_utils.py to check health
    if python "${SCRIPT_DIR}/db_utils.py" health; then
        log "SUCCESS" "Database health verification passed"
    else
        log "WARN" "Database health verification failed"
    fi
}

# Show database status
show_status() {
    log "INFO" "Final database status:"
    
    # Create temporary status script
    local status_script="${PROJECT_ROOT}/temp_status_script.py"
    
    cat > "$status_script" << 'EOF'
#!/usr/bin/env python3
"""
Database status script
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def show_database_status():
    """Show database status and table information."""
    from app.db.database import get_db_session
    from app.core.logging import logger
    
    try:
        async with get_db_session() as session:
            # Get table information
            result = await session.execute("""
                SELECT 
                    table_name,
                    (SELECT COUNT(*) FROM information_schema.columns 
                     WHERE table_name = t.table_name AND table_schema = 'public') as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            
            tables = result.fetchall()
            
            if tables:
                print(f"\nDatabase Tables ({len(tables)} total):")
                print("-" * 50)
                for table in tables:
                    print(f"  {table.table_name} ({table.column_count} columns)")
                print("-" * 50)
            else:
                print("No tables found in database")
                
            # Get migration version
            try:
                version_result = await session.execute(
                    "SELECT version_num FROM alembic_version"
                )
                version = version_result.scalar()
                if version:
                    print(f"Current migration version: {version}")
                else:
                    print("No migration version found")
            except Exception:
                print("Migration version table not found")
                
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(show_database_status())
EOF
    
    cd "$PROJECT_ROOT"
    
    if python "$status_script"; then
        log "SUCCESS" "Database status retrieved"
    else
        log "WARN" "Failed to retrieve database status"
    fi
    
    # Clean up temporary script
    rm -f "$status_script"
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Database Reset Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -f, --force             Skip confirmation prompt
    --no-seed               Skip database seeding
    --seed-type TYPE        Type of seed data (default: all)
    --seed-count COUNT      Number of seed records (default: 10)
    --no-verify             Skip database health verification

SEED TYPES:
    all                     Create sample data for all entity types
    users                   Create sample users only
    ssh                     Create sample SSH connections
    commands               Create sample commands
    sessions               Create sample sessions
    sync                   Create sample sync data

EXAMPLES:
    $0                      # Reset with confirmation and default seeding
    $0 -f                   # Reset without confirmation
    $0 --no-seed           # Reset without seeding
    $0 --seed-type users   # Reset and seed users only
    $0 -f --seed-count 25  # Reset and create 25 seed records per type

OPERATION SEQUENCE:
    1. Confirmation prompt (unless --force)
    2. Drop existing database
    3. Create new database
    4. Initialize database structure
    5. Run Alembic migrations
    6. Seed with sample data (unless --no-seed)
    7. Verify database health (unless --no-verify)
    8. Show final status

WARNING:
    This operation is destructive and will permanently delete all data!
    Make sure you have backups if needed.

ENVIRONMENT:
    Uses same database connection settings as main application.
    Set DATABASE_URL or individual variables in .env file.

EOF
}

# Main function
main() {
    local force=false
    local skip_seed=false
    local seed_type="all"
    local seed_count=10
    local skip_verify=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--force)
                force=true
                ;;
            --no-seed)
                skip_seed=true
                ;;
            --seed-type)
                if [[ -n "${2:-}" ]]; then
                    seed_type="$2"
                    shift
                else
                    log "ERROR" "Seed type required with --seed-type option"
                    exit 1
                fi
                ;;
            --seed-count)
                if [[ -n "${2:-}" ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
                    seed_count="$2"
                    shift
                else
                    log "ERROR" "Valid seed count required with --seed-count option"
                    exit 1
                fi
                ;;
            --no-verify)
                skip_verify=true
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                log "ERROR" "Unexpected argument: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done
    
    # Validate seed type
    case "$seed_type" in
        all|users|ssh|commands|sessions|sync)
            # Valid seed type
            ;;
        *)
            log "ERROR" "Invalid seed type: $seed_type"
            log "INFO" "Valid types: all, users, ssh, commands, sessions, sync"
            exit 1
            ;;
    esac
    
    log "INFO" "Starting database reset script..."
    log "INFO" "Project root: $PROJECT_ROOT"
    
    # Check requirements
    check_requirements
    
    # Activate virtual environment
    activate_venv
    
    # Confirm destructive operation
    confirm_reset "$force"
    
    # Perform reset sequence
    log "INFO" "=== Database Reset Sequence Started ==="
    
    # Step 1: Reset database structure
    reset_database
    
    # Step 2: Run migrations
    run_migrations
    
    # Step 3: Seed database (optional)
    seed_database "$seed_type" "$seed_count" "$skip_seed"
    
    # Step 4: Verify database health (optional)
    if [[ "$skip_verify" != true ]]; then
        verify_database
    fi
    
    # Step 5: Show final status
    show_status
    
    log "SUCCESS" "=== Database Reset Sequence Completed Successfully ==="
    
    # Show next steps
    echo
    log "INFO" "Database is now ready for use"
    log "INFO" "You can start the application with: python main.py"
    log "INFO" "Or run tests with: pytest"
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"