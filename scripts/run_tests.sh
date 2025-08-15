#!/bin/bash
# DevPocket API - Test Runner Script
# Runs pytest with coverage and comprehensive reporting

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

# Check if pytest is available
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        log "ERROR" "pytest not found. Please install requirements: pip install -r requirements.txt"
        exit 1
    fi
    log "SUCCESS" "pytest found"
}

# Setup test environment
setup_test_env() {
    log "INFO" "Setting up test environment..."
    
    # Export test environment variables (in addition to pytest.ini)
    export ENVIRONMENT=test
    export TESTING=true
    export APP_DEBUG=true
    
    # Use test database if not already set
    if [[ -z "${DATABASE_URL:-}" ]]; then
        export DATABASE_URL="postgresql://test:test@localhost:5433/devpocket_test"
        log "INFO" "Using default test database URL"
    fi
    
    # Use test Redis if not already set
    if [[ -z "${REDIS_URL:-}" ]]; then
        export REDIS_URL="redis://localhost:6380"
        log "INFO" "Using default test Redis URL"
    fi
    
    log "SUCCESS" "Test environment configured"
}

# Check if test database is available
check_test_database() {
    local skip_db_check="$1"
    
    if [[ "$skip_db_check" == true ]]; then
        log "INFO" "Skipping database check"
        return 0
    fi
    
    log "INFO" "Checking test database connection..."
    
    # Create a simple database check script
    local db_check_script="${PROJECT_ROOT}/temp_db_check.py"
    
    cat > "$db_check_script" << 'EOF'
#!/usr/bin/env python3
import os
import sys
import asyncio
import asyncpg

async def check_test_db():
    """Check test database connection."""
    try:
        # Get database URL from environment
        db_url = os.getenv('DATABASE_URL', 'postgresql://test:test@localhost:5433/devpocket_test')
        
        # Try to connect
        conn = await asyncpg.connect(db_url)
        await conn.fetchval("SELECT 1")
        await conn.close()
        
        print("✅ Test database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Test database connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_test_db())
    sys.exit(0 if result else 1)
EOF
    
    cd "$PROJECT_ROOT"
    
    if python "$db_check_script"; then
        log "SUCCESS" "Test database is accessible"
    else
        log "WARN" "Test database not accessible - some tests may fail"
        log "INFO" "Consider running: docker-compose up -d postgres-test"
    fi
    
    # Clean up
    rm -f "$db_check_script"
}

# Create test reports directory
setup_reports_dir() {
    local reports_dir="${PROJECT_ROOT}/test-reports"
    
    if [[ ! -d "$reports_dir" ]]; then
        mkdir -p "$reports_dir"
        log "INFO" "Created test reports directory: $reports_dir"
    fi
    
    # Create coverage reports directory
    local coverage_dir="${PROJECT_ROOT}/htmlcov"
    if [[ -d "$coverage_dir" ]]; then
        log "INFO" "Coverage directory exists: $coverage_dir"
    fi
}

# Run pytest with various configurations
run_tests() {
    local test_type="$1"
    local test_path="$2"
    local markers="$3"
    local extra_args="$4"
    local parallel="$5"
    local verbose="$6"
    local coverage="$7"
    
    log "INFO" "Running tests (type: $test_type)..."
    
    cd "$PROJECT_ROOT"
    
    # Base pytest command
    local pytest_cmd="pytest"
    
    # Add test path if specified
    if [[ -n "$test_path" ]]; then
        pytest_cmd="$pytest_cmd $test_path"
    else
        pytest_cmd="$pytest_cmd tests/"
    fi
    
    # Add markers if specified
    if [[ -n "$markers" ]]; then
        pytest_cmd="$pytest_cmd -m \"$markers\""
    fi
    
    # Add verbosity
    if [[ "$verbose" == true ]]; then
        pytest_cmd="$pytest_cmd -v"
    else
        pytest_cmd="$pytest_cmd -q"
    fi
    
    # Add parallel execution
    if [[ "$parallel" == true ]]; then
        # Use number of CPU cores
        local num_cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
        pytest_cmd="$pytest_cmd -n $num_cores"
    fi
    
    # Coverage options
    if [[ "$coverage" == true ]]; then
        pytest_cmd="$pytest_cmd --cov=app --cov-report=term-missing:skip-covered --cov-report=html:htmlcov --cov-report=xml:coverage.xml"
    else
        pytest_cmd="$pytest_cmd --no-cov"
    fi
    
    # Add HTML report
    pytest_cmd="$pytest_cmd --html=test-reports/report.html --self-contained-html"
    
    # Add JUnit XML report for CI
    pytest_cmd="$pytest_cmd --junit-xml=test-reports/junit.xml"
    
    # Add extra arguments
    if [[ -n "$extra_args" ]]; then
        pytest_cmd="$pytest_cmd $extra_args"
    fi
    
    log "INFO" "Executing: $pytest_cmd"
    
    # Run the tests
    local exit_code=0
    if ! eval "$pytest_cmd"; then
        exit_code=$?
        log "ERROR" "Tests failed with exit code $exit_code"
    else
        log "SUCCESS" "All tests passed"
    fi
    
    return $exit_code
}

# Show test results summary
show_test_summary() {
    local coverage="$1"
    
    log "INFO" "Test execution summary:"
    
    # Show coverage report location
    if [[ "$coverage" == true ]]; then
        local coverage_file="${PROJECT_ROOT}/htmlcov/index.html"
        if [[ -f "$coverage_file" ]]; then
            log "INFO" "Coverage report: file://$coverage_file"
        fi
        
        # Show coverage XML location
        local coverage_xml="${PROJECT_ROOT}/coverage.xml"
        if [[ -f "$coverage_xml" ]]; then
            log "INFO" "Coverage XML: $coverage_xml"
        fi
    fi
    
    # Show HTML test report location
    local html_report="${PROJECT_ROOT}/test-reports/report.html"
    if [[ -f "$html_report" ]]; then
        log "INFO" "Test report: file://$html_report"
    fi
    
    # Show JUnit XML location
    local junit_xml="${PROJECT_ROOT}/test-reports/junit.xml"
    if [[ -f "$junit_xml" ]]; then
        log "INFO" "JUnit XML: $junit_xml"
    fi
}

# Clean previous test artifacts
clean_artifacts() {
    log "INFO" "Cleaning previous test artifacts..."
    
    # Remove coverage files
    rm -rf "${PROJECT_ROOT}/htmlcov"
    rm -f "${PROJECT_ROOT}/coverage.xml"
    rm -f "${PROJECT_ROOT}/.coverage"
    
    # Remove test reports
    rm -rf "${PROJECT_ROOT}/test-reports"
    
    # Remove pytest cache
    rm -rf "${PROJECT_ROOT}/.pytest_cache"
    
    # Remove Python cache
    find "${PROJECT_ROOT}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*.pyc" -delete 2>/dev/null || true
    
    log "SUCCESS" "Test artifacts cleaned"
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Test Runner Script

USAGE:
    $0 [OPTIONS] [TEST_PATH]

OPTIONS:
    -h, --help              Show this help message
    -t, --type TYPE         Test type: unit, integration, api, all (default: all)
    -m, --markers MARKERS   Pytest markers to run (e.g., "unit and not slow")
    -p, --parallel          Run tests in parallel
    -v, --verbose           Verbose output
    -q, --quiet             Quiet output (opposite of verbose)
    --no-cov                Disable coverage reporting
    --no-db-check           Skip database connectivity check
    --clean                 Clean test artifacts before running
    --clean-only            Only clean artifacts, don't run tests
    --summary-only          Show summary of available tests
    
TEST TYPES:
    all                     Run all tests (default)
    unit                    Run unit tests only
    integration            Run integration tests only  
    api                     Run API endpoint tests only
    websocket              Run WebSocket tests only
    auth                   Run authentication tests only
    database               Run database tests only
    services               Run service layer tests only
    security               Run security tests only
    performance            Run performance tests only
    external               Run tests requiring external services

ARGUMENTS:
    TEST_PATH              Specific test file or directory to run

EXAMPLES:
    $0                          # Run all tests with coverage
    $0 -t unit                  # Run unit tests only
    $0 -p -v                    # Run all tests in parallel with verbose output
    $0 -m "not slow"           # Run tests excluding slow ones
    $0 tests/test_auth/        # Run tests in specific directory
    $0 tests/test_api/test_auth_endpoints.py::test_login  # Run specific test
    $0 --clean -t api          # Clean artifacts and run API tests
    $0 --no-cov -q            # Run tests without coverage, quietly
    $0 --summary-only          # Show test structure summary

REPORTS:
    Generated reports will be saved in:
    - HTML coverage: htmlcov/index.html
    - XML coverage: coverage.xml
    - HTML test report: test-reports/report.html
    - JUnit XML: test-reports/junit.xml

ENVIRONMENT:
    Test environment settings are configured in pytest.ini.
    Override with environment variables if needed:
    - DATABASE_URL (test database)
    - REDIS_URL (test Redis)
    - TESTING=true (automatically set)

EOF
}

# Show test summary without running
show_test_structure() {
    log "INFO" "Available test structure:"
    
    cd "$PROJECT_ROOT"
    
    if [[ -d "tests" ]]; then
        echo
        echo "Test Directory Structure:"
        tree tests/ 2>/dev/null || find tests/ -type f -name "*.py" | sort
        echo
        
        # Show available markers
        log "INFO" "Available pytest markers:"
        pytest --markers | grep -E "^@pytest.mark" || echo "No custom markers found"
        echo
        
        # Count tests by type
        local total_tests=$(find tests/ -name "test_*.py" -o -name "*_test.py" | wc -l)
        log "INFO" "Total test files: $total_tests"
        
        # Show test counts by marker (if pytest is available)
        if command -v pytest &> /dev/null; then
            log "INFO" "Test counts by marker:"
            pytest --collect-only -q | grep -E "^[0-9]+ tests collected" || true
        fi
    else
        log "WARN" "No tests directory found"
    fi
}

# Main function
main() {
    local test_type="all"
    local test_path=""
    local markers=""
    local extra_args=""
    local parallel=false
    local verbose=false
    local coverage=true
    local skip_db_check=false
    local clean_artifacts_flag=false
    local clean_only=false
    local summary_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -t|--type)
                if [[ -n "${2:-}" ]]; then
                    test_type="$2"
                    shift
                else
                    log "ERROR" "Test type required with -t/--type option"
                    exit 1
                fi
                ;;
            -m|--markers)
                if [[ -n "${2:-}" ]]; then
                    markers="$2"
                    shift
                else
                    log "ERROR" "Markers required with -m/--markers option"
                    exit 1
                fi
                ;;
            -p|--parallel)
                parallel=true
                ;;
            -v|--verbose)
                verbose=true
                ;;
            -q|--quiet)
                verbose=false
                ;;
            --no-cov)
                coverage=false
                ;;
            --no-db-check)
                skip_db_check=true
                ;;
            --clean)
                clean_artifacts_flag=true
                ;;
            --clean-only)
                clean_only=true
                ;;
            --summary-only)
                summary_only=true
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                test_path="$1"
                ;;
        esac
        shift
    done
    
    # Handle special modes
    if [[ "$clean_only" == true ]]; then
        activate_venv
        clean_artifacts
        exit 0
    fi
    
    if [[ "$summary_only" == true ]]; then
        show_test_structure
        exit 0
    fi
    
    # Validate test type and set markers accordingly
    case "$test_type" in
        all)
            # Run all tests, no specific markers
            ;;
        unit)
            markers="${markers:+$markers and }unit"
            ;;
        integration)
            markers="${markers:+$markers and }integration"
            ;;
        api)
            markers="${markers:+$markers and }api"
            ;;
        websocket)
            markers="${markers:+$markers and }websocket"
            ;;
        auth)
            markers="${markers:+$markers and }auth"
            ;;
        database)
            markers="${markers:+$markers and }database"
            ;;
        services)
            markers="${markers:+$markers and }services"
            ;;
        security)
            markers="${markers:+$markers and }security"
            ;;
        performance)
            markers="${markers:+$markers and }performance"
            ;;
        external)
            markers="${markers:+$markers and }external"
            ;;
        *)
            log "ERROR" "Invalid test type: $test_type"
            log "INFO" "Valid types: all, unit, integration, api, websocket, auth, database, services, security, performance, external"
            exit 1
            ;;
    esac
    
    log "INFO" "Starting test runner script..."
    log "INFO" "Project root: $PROJECT_ROOT"
    log "INFO" "Test type: $test_type"
    if [[ -n "$markers" ]]; then
        log "INFO" "Markers: $markers"
    fi
    if [[ -n "$test_path" ]]; then
        log "INFO" "Test path: $test_path"
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Check pytest availability
    check_pytest
    
    # Clean artifacts if requested
    if [[ "$clean_artifacts_flag" == true ]]; then
        clean_artifacts
    fi
    
    # Setup test environment
    setup_test_env
    
    # Setup reports directory
    setup_reports_dir
    
    # Check test database
    check_test_database "$skip_db_check"
    
    # Run tests
    local exit_code=0
    run_tests "$test_type" "$test_path" "$markers" "$extra_args" "$parallel" "$verbose" "$coverage" || exit_code=$?
    
    # Show summary
    show_test_summary "$coverage"
    
    if [[ $exit_code -eq 0 ]]; then
        log "SUCCESS" "Test runner completed successfully"
    else
        log "ERROR" "Test runner completed with failures"
    fi
    
    exit $exit_code
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"