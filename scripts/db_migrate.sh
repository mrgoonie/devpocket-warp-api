#!/bin/bash
# DevPocket API - Database Migration Script
# Runs Alembic migrations with proper error handling and logging

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

# Check if Alembic is available
check_alembic() {
    if ! command -v alembic &> /dev/null; then
        log "ERROR" "Alembic not found. Please install requirements: pip install -r requirements.txt"
        exit 1
    fi
    log "SUCCESS" "Alembic found"
}

# Check database connection using db_utils.py
check_database() {
    log "INFO" "Checking database connection..."
    
    if python "${SCRIPT_DIR}/db_utils.py" test; then
        log "SUCCESS" "Database connection verified"
    else
        log "ERROR" "Database connection failed"
        log "INFO" "Please ensure PostgreSQL is running and connection settings are correct"
        exit 1
    fi
}

# Run Alembic migrations
run_migrations() {
    local target="${1:-head}"
    
    log "INFO" "Running Alembic migrations to target: $target"
    
    # Change to project root for Alembic operations
    cd "$PROJECT_ROOT"
    
    # Check current migration status
    log "INFO" "Current migration status:"
    if ! alembic current; then
        log "ERROR" "Failed to get current migration status"
        exit 1
    fi
    
    # Show pending migrations
    log "INFO" "Checking for pending migrations..."
    if alembic show "$target" &> /dev/null; then
        # Run the migration
        if alembic upgrade "$target"; then
            log "SUCCESS" "Migration completed successfully"
        else
            log "ERROR" "Migration failed"
            exit 1
        fi
    else
        log "ERROR" "Invalid migration target: $target"
        exit 1
    fi
    
    # Show final status
    log "INFO" "Final migration status:"
    alembic current
}

# Generate new migration (optional feature)
generate_migration() {
    local message="$1"
    
    log "INFO" "Generating new migration: $message"
    
    cd "$PROJECT_ROOT"
    
    if alembic revision --autogenerate -m "$message"; then
        log "SUCCESS" "Migration generated successfully"
        log "INFO" "Please review the generated migration file before running db_migrate.sh"
    else
        log "ERROR" "Failed to generate migration"
        exit 1
    fi
}

# Show migration history
show_history() {
    log "INFO" "Migration history:"
    cd "$PROJECT_ROOT"
    alembic history --verbose
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Database Migration Script

USAGE:
    $0 [OPTIONS] [TARGET]

OPTIONS:
    -h, --help              Show this help message
    -g, --generate MESSAGE  Generate new migration with message
    --history              Show migration history
    --check-only           Only check database connection, don't run migrations

ARGUMENTS:
    TARGET                  Migration target (default: head)
                           - head: Migrate to latest
                           - +1: Migrate one step forward
                           - -1: Migrate one step backward
                           - <revision>: Migrate to specific revision

EXAMPLES:
    $0                      # Migrate to latest (head)
    $0 head                 # Migrate to latest
    $0 +1                   # Migrate one step forward
    $0 -1                   # Migrate one step backward
    $0 abc123               # Migrate to specific revision
    $0 -g "Add user table"  # Generate new migration
    $0 --history           # Show migration history
    $0 --check-only        # Only check database connection

ENVIRONMENT:
    Set DATABASE_URL or individual database connection variables in .env file.
    
    Required environment variables:
    - DATABASE_HOST (default: localhost)
    - DATABASE_PORT (default: 5432) 
    - DATABASE_USER (default: devpocket_user)
    - DATABASE_PASSWORD
    - DATABASE_NAME (default: devpocket_warp_dev)

EOF
}

# Main function
main() {
    local target="head"
    local generate_msg=""
    local show_history_flag=false
    local check_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -g|--generate)
                if [[ -n "${2:-}" ]]; then
                    generate_msg="$2"
                    shift
                else
                    log "ERROR" "Migration message required with -g/--generate option"
                    exit 1
                fi
                ;;
            --history)
                show_history_flag=true
                ;;
            --check-only)
                check_only=true
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                target="$1"
                ;;
        esac
        shift
    done
    
    log "INFO" "Starting database migration script..."
    log "INFO" "Project root: $PROJECT_ROOT"
    
    # Activate virtual environment
    activate_venv
    
    # Check if Alembic is available
    check_alembic
    
    # Check database connection
    check_database
    
    # Handle different operations
    if [[ -n "$generate_msg" ]]; then
        generate_migration "$generate_msg"
    elif [[ "$show_history_flag" == true ]]; then
        show_history
    elif [[ "$check_only" == true ]]; then
        log "SUCCESS" "Database connection check completed"
    else
        run_migrations "$target"
    fi
    
    log "SUCCESS" "Database migration script completed successfully"
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"