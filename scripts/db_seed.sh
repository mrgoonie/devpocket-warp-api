#!/bin/bash
# DevPocket API - Database Seeding Script
# Seeds database with sample data using existing factories

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

# Check database connection
check_database() {
    log "INFO" "Checking database connection..."
    
    if python "${SCRIPT_DIR}/db_utils.py" test; then
        log "SUCCESS" "Database connection verified"
    else
        log "ERROR" "Database connection failed"
        log "INFO" "Please ensure PostgreSQL is running and migrations are up to date"
        exit 1
    fi
}

# Create seeding script and run it
run_seeding() {
    local seed_type="$1"
    local count="$2"
    
    log "INFO" "Creating seed data (type: $seed_type, count: $count)..."
    
    # Create temporary seeding script
    local seed_script="${PROJECT_ROOT}/temp_seed_script.py"
    
    cat > "$seed_script" << 'EOF'
#!/usr/bin/env python3
"""
Temporary seeding script for DevPocket API
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def seed_database(seed_type: str, count: int = 10):
    """Seed database with sample data using factories."""
    
    # Import required modules
    from app.db.database import get_db_session
    from app.core.config import settings
    from app.core.logging import logger
    
    # Import factories
    from tests.factories.user_factory import UserFactory
    from tests.factories.ssh_factory import SSHConnectionFactory
    from tests.factories.command_factory import CommandFactory
    from tests.factories.session_factory import SessionFactory
    from tests.factories.sync_factory import SyncDataFactory
    
    logger.info(f"Starting database seeding (type: {seed_type}, count: {count})")
    
    try:
        # Get database session
        async with get_db_session() as session:
            
            if seed_type in ["all", "users"]:
                logger.info(f"Creating {count} sample users...")
                users = []
                for i in range(count):
                    user = await UserFactory.create_async(session=session)
                    users.append(user)
                logger.info(f"Created {len(users)} users")
            
            if seed_type in ["all", "ssh"]:
                logger.info(f"Creating {count} sample SSH connections...")
                ssh_connections = []
                for i in range(count):
                    # Create user first if not already created
                    if seed_type != "all":
                        user = await UserFactory.create_async(session=session)
                    else:
                        user = users[i % len(users)] if users else await UserFactory.create_async(session=session)
                    
                    ssh_conn = await SSHConnectionFactory.create_async(
                        session=session,
                        user_id=user.id
                    )
                    ssh_connections.append(ssh_conn)
                logger.info(f"Created {len(ssh_connections)} SSH connections")
            
            if seed_type in ["all", "commands"]:
                logger.info(f"Creating {count} sample commands...")
                commands = []
                for i in range(count):
                    # Create user first if not already created
                    if seed_type not in ["all", "ssh"]:
                        user = await UserFactory.create_async(session=session)
                    else:
                        user = users[i % len(users)] if 'users' in locals() else await UserFactory.create_async(session=session)
                    
                    command = await CommandFactory.create_async(
                        session=session,
                        user_id=user.id
                    )
                    commands.append(command)
                logger.info(f"Created {len(commands)} commands")
            
            if seed_type in ["all", "sessions"]:
                logger.info(f"Creating {count} sample sessions...")
                sessions = []
                for i in range(count):
                    # Create user first if not already created
                    if seed_type not in ["all", "ssh", "commands"]:
                        user = await UserFactory.create_async(session=session)
                    else:
                        user = users[i % len(users)] if 'users' in locals() else await UserFactory.create_async(session=session)
                    
                    session_obj = await SessionFactory.create_async(
                        session=session,
                        user_id=user.id
                    )
                    sessions.append(session_obj)
                logger.info(f"Created {len(sessions)} sessions")
            
            if seed_type in ["all", "sync"]:
                logger.info(f"Creating {count} sample sync data...")
                sync_data = []
                for i in range(count):
                    # Create user first if not already created
                    if seed_type not in ["all", "ssh", "commands", "sessions"]:
                        user = await UserFactory.create_async(session=session)
                    else:
                        user = users[i % len(users)] if 'users' in locals() else await UserFactory.create_async(session=session)
                    
                    sync_obj = await SyncDataFactory.create_async(
                        session=session,
                        user_id=user.id
                    )
                    sync_data.append(sync_obj)
                logger.info(f"Created {len(sync_data)} sync data records")
            
            # Commit all changes
            await session.commit()
            logger.info("Database seeding completed successfully")
            
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise

async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python temp_seed_script.py <seed_type> <count>")
        sys.exit(1)
    
    seed_type = sys.argv[1]
    count = int(sys.argv[2])
    
    await seed_database(seed_type, count)

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    # Run the seeding script
    cd "$PROJECT_ROOT"
    
    if python "$seed_script" "$seed_type" "$count"; then
        log "SUCCESS" "Database seeding completed successfully"
    else
        log "ERROR" "Database seeding failed"
        rm -f "$seed_script"
        exit 1
    fi
    
    # Clean up temporary script
    rm -f "$seed_script"
}

# Show database statistics
show_stats() {
    log "INFO" "Fetching database statistics..."
    
    # Create temporary stats script
    local stats_script="${PROJECT_ROOT}/temp_stats_script.py"
    
    cat > "$stats_script" << 'EOF'
#!/usr/bin/env python3
"""
Database statistics script
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def show_database_stats():
    """Show database table statistics."""
    from app.db.database import get_db_session
    from app.core.logging import logger
    
    try:
        async with get_db_session() as session:
            # Query table statistics
            result = await session.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables 
                ORDER BY tablename;
            """)
            
            stats = result.fetchall()
            
            if stats:
                print("\nDatabase Table Statistics:")
                print("-" * 80)
                print(f"{'Table':<20} {'Live Rows':<12} {'Inserts':<10} {'Updates':<10} {'Deletes':<10}")
                print("-" * 80)
                
                for stat in stats:
                    print(f"{stat.tablename:<20} {stat.live_rows:<12} {stat.inserts:<10} {stat.updates:<10} {stat.deletes:<10}")
                
                print("-" * 80)
                print(f"Total tables: {len(stats)}")
            else:
                print("No table statistics available")
                
    except Exception as e:
        logger.error(f"Failed to fetch database statistics: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(show_database_stats())
EOF
    
    cd "$PROJECT_ROOT"
    
    if python "$stats_script"; then
        log "SUCCESS" "Database statistics retrieved"
    else
        log "WARN" "Failed to retrieve database statistics"
    fi
    
    # Clean up temporary script
    rm -f "$stats_script"
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Database Seeding Script

USAGE:
    $0 [OPTIONS] [SEED_TYPE] [COUNT]

OPTIONS:
    -h, --help          Show this help message
    --stats             Show database statistics after seeding
    --stats-only        Only show database statistics, don't seed

ARGUMENTS:
    SEED_TYPE           Type of data to seed (default: all)
                       Options: all, users, ssh, commands, sessions, sync
    COUNT              Number of records to create per type (default: 10)

SEED TYPES:
    all                Create sample data for all entity types
    users              Create sample users only
    ssh                Create sample SSH connections (with users)
    commands           Create sample commands (with users) 
    sessions           Create sample sessions (with users)
    sync               Create sample sync data (with users)

EXAMPLES:
    $0                          # Seed all types with 10 records each
    $0 users 25                 # Create 25 sample users
    $0 ssh 15                   # Create 15 SSH connections (with users)
    $0 all 5                    # Create 5 records of each type
    $0 --stats-only             # Show database statistics only
    $0 commands 20 --stats      # Create 20 commands and show stats

PREREQUISITES:
    - Database must be running and accessible
    - Database migrations must be up to date (run db_migrate.sh first)
    - Test factories must be available in tests/factories/

ENVIRONMENT:
    Uses same database connection settings as main application.
    Set DATABASE_URL or individual variables in .env file.

EOF
}

# Main function
main() {
    local seed_type="all"
    local count=10
    local show_stats_flag=false
    local stats_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --stats)
                show_stats_flag=true
                ;;
            --stats-only)
                stats_only=true
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ "$1" =~ ^[0-9]+$ ]]; then
                    count="$1"
                else
                    seed_type="$1"
                fi
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
    
    log "INFO" "Starting database seeding script..."
    log "INFO" "Project root: $PROJECT_ROOT"
    log "INFO" "Seed type: $seed_type"
    log "INFO" "Count: $count"
    
    # Activate virtual environment
    activate_venv
    
    # Check database connection
    check_database
    
    # Handle stats-only mode
    if [[ "$stats_only" == true ]]; then
        show_stats
        exit 0
    fi
    
    # Run seeding
    run_seeding "$seed_type" "$count"
    
    # Show stats if requested
    if [[ "$show_stats_flag" == true ]]; then
        show_stats
    fi
    
    log "SUCCESS" "Database seeding script completed successfully"
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"