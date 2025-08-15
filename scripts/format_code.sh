#!/bin/bash
# DevPocket API - Code Formatting and Quality Script
# Runs black, ruff, mypy with proper exit codes and reporting

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

# Check if formatting tools are available
check_tools() {
    local missing_tools=()
    
    if ! command -v black &> /dev/null; then
        missing_tools+=("black")
    fi
    
    if ! command -v ruff &> /dev/null; then
        missing_tools+=("ruff")
    fi
    
    if ! command -v mypy &> /dev/null; then
        missing_tools+=("mypy")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log "ERROR" "Missing tools: ${missing_tools[*]}"
        log "INFO" "Please install requirements: pip install -r requirements.txt"
        exit 1
    fi
    
    log "SUCCESS" "All formatting tools found"
}

# Get Python files to format
get_python_files() {
    local target_path="$1"
    
    if [[ -f "$target_path" ]]; then
        # Single file
        echo "$target_path"
    elif [[ -d "$target_path" ]]; then
        # Directory - find Python files
        find "$target_path" -name "*.py" -type f | grep -v __pycache__ | sort
    else
        log "ERROR" "Target path does not exist: $target_path"
        exit 1
    fi
}

# Run Black formatter
run_black() {
    local target="$1"
    local check_only="$2"
    local diff_only="$3"
    
    log "INFO" "Running Black formatter..."
    
    cd "$PROJECT_ROOT"
    
    local black_cmd="black"
    local black_args=()
    
    # Configuration options
    black_args+=("--line-length" "88")
    black_args+=("--target-version" "py311")
    black_args+=("--include" '\.pyi?$')
    black_args+=("--extend-exclude" "migrations/")
    
    # Mode options
    if [[ "$check_only" == true ]]; then
        black_args+=("--check")
        log "INFO" "Running Black in check mode (no changes will be made)"
    fi
    
    if [[ "$diff_only" == true ]]; then
        black_args+=("--diff")
    fi
    
    # Add verbosity
    black_args+=("--verbose")
    
    # Add target
    black_args+=("$target")
    
    # Execute Black
    local exit_code=0
    if ! "$black_cmd" "${black_args[@]}"; then
        exit_code=$?
        if [[ "$check_only" == true ]]; then
            log "WARN" "Black found formatting issues (exit code: $exit_code)"
        else
            log "ERROR" "Black formatting failed (exit code: $exit_code)"
        fi
    else
        if [[ "$check_only" == true ]]; then
            log "SUCCESS" "Black check passed - no formatting issues"
        else
            log "SUCCESS" "Black formatting completed"
        fi
    fi
    
    return $exit_code
}

# Run Ruff linter
run_ruff() {
    local target="$1"
    local check_only="$2"
    local fix_mode="$3"
    
    log "INFO" "Running Ruff linter..."
    
    cd "$PROJECT_ROOT"
    
    local ruff_cmd="ruff"
    local ruff_args=()
    
    if [[ "$fix_mode" == true ]] && [[ "$check_only" != true ]]; then
        # Fix mode
        ruff_args+=("check")
        ruff_args+=("--fix")
        log "INFO" "Running Ruff in fix mode"
    else
        # Check mode
        ruff_args+=("check")
        log "INFO" "Running Ruff in check mode"
    fi
    
    # Configuration options
    ruff_args+=("--output-format" "full")
    
    # Add target
    ruff_args+=("$target")
    
    # Execute Ruff
    local exit_code=0
    if ! "$ruff_cmd" "${ruff_args[@]}"; then
        exit_code=$?
        if [[ "$check_only" == true ]]; then
            log "WARN" "Ruff found linting issues (exit code: $exit_code)"
        else
            log "ERROR" "Ruff linting failed (exit code: $exit_code)"
        fi
    else
        log "SUCCESS" "Ruff linting passed"
    fi
    
    return $exit_code
}

# Run Ruff format
run_ruff_format() {
    local target="$1"
    local check_only="$2"
    local diff_only="$3"
    
    log "INFO" "Running Ruff formatter..."
    
    cd "$PROJECT_ROOT"
    
    local ruff_cmd="ruff"
    local ruff_args=("format")
    
    # Mode options
    if [[ "$check_only" == true ]]; then
        ruff_args+=("--check")
        log "INFO" "Running Ruff format in check mode"
    fi
    
    if [[ "$diff_only" == true ]]; then
        ruff_args+=("--diff")
    fi
    
    # Add target
    ruff_args+=("$target")
    
    # Execute Ruff format
    local exit_code=0
    if ! "$ruff_cmd" "${ruff_args[@]}"; then
        exit_code=$?
        if [[ "$check_only" == true ]]; then
            log "WARN" "Ruff format found formatting issues (exit code: $exit_code)"
        else
            log "ERROR" "Ruff formatting failed (exit code: $exit_code)"
        fi
    else
        if [[ "$check_only" == true ]]; then
            log "SUCCESS" "Ruff format check passed"
        else
            log "SUCCESS" "Ruff formatting completed"
        fi
    fi
    
    return $exit_code
}

# Run MyPy type checker
run_mypy() {
    local target="$1"
    local strict_mode="$2"
    
    log "INFO" "Running MyPy type checker..."
    
    cd "$PROJECT_ROOT"
    
    local mypy_cmd="mypy"
    local mypy_args=()
    
    # Configuration options
    mypy_args+=("--python-version" "3.11")
    mypy_args+=("--show-error-codes")
    mypy_args+=("--show-error-context")
    mypy_args+=("--pretty")
    
    # Strictness options
    if [[ "$strict_mode" == true ]]; then
        mypy_args+=("--strict")
        log "INFO" "Running MyPy in strict mode"
    else
        # Custom configuration for gradual typing
        mypy_args+=("--ignore-missing-imports")
        mypy_args+=("--disallow-untyped-defs")
        mypy_args+=("--check-untyped-defs")
        mypy_args+=("--warn-redundant-casts")
        mypy_args+=("--warn-unused-ignores")
        log "INFO" "Running MyPy with standard configuration"
    fi
    
    # Exclude patterns
    mypy_args+=("--exclude" "migrations/")
    mypy_args+=("--exclude" "__pycache__/")
    
    # Add target
    mypy_args+=("$target")
    
    # Execute MyPy
    local exit_code=0
    if ! "$mypy_cmd" "${mypy_args[@]}"; then
        exit_code=$?
        log "WARN" "MyPy found type issues (exit code: $exit_code)"
    else
        log "SUCCESS" "MyPy type checking passed"
    fi
    
    return $exit_code
}

# Generate quality report
generate_report() {
    local target="$1"
    local report_file="${PROJECT_ROOT}/code-quality-report.txt"
    
    log "INFO" "Generating code quality report..."
    
    cat > "$report_file" << EOF
DevPocket API - Code Quality Report
Generated: $(date)
Target: $target

========================================
SUMMARY
========================================

EOF
    
    # Count Python files
    local python_files
    python_files=$(get_python_files "$target" | wc -l)
    echo "Python files analyzed: $python_files" >> "$report_file"
    
    # Add line counts
    local total_lines
    total_lines=$(get_python_files "$target" | xargs wc -l | tail -n 1 | awk '{print $1}')
    echo "Total lines of code: $total_lines" >> "$report_file"
    echo "" >> "$report_file"
    
    # Run tools in report mode
    echo "========================================" >> "$report_file"
    echo "BLACK FORMATTER CHECK" >> "$report_file"
    echo "========================================" >> "$report_file"
    
    if black --check --diff "$target" >> "$report_file" 2>&1; then
        echo "✅ Black: No formatting issues found" >> "$report_file"
    else
        echo "❌ Black: Formatting issues found" >> "$report_file"
    fi
    echo "" >> "$report_file"
    
    echo "========================================" >> "$report_file"
    echo "RUFF LINTER CHECK" >> "$report_file"
    echo "========================================" >> "$report_file"
    
    if ruff check "$target" >> "$report_file" 2>&1; then
        echo "✅ Ruff: No linting issues found" >> "$report_file"
    else
        echo "❌ Ruff: Linting issues found" >> "$report_file"
    fi
    echo "" >> "$report_file"
    
    echo "========================================" >> "$report_file"
    echo "MYPY TYPE CHECK" >> "$report_file"
    echo "========================================" >> "$report_file"
    
    if mypy "$target" >> "$report_file" 2>&1; then
        echo "✅ MyPy: No type issues found" >> "$report_file"
    else
        echo "❌ MyPy: Type issues found" >> "$report_file"
    fi
    
    log "SUCCESS" "Code quality report generated: $report_file"
}

# Show statistics
show_stats() {
    local target="$1"
    
    log "INFO" "Code statistics for: $target"
    
    # Count files
    local python_files
    python_files=$(get_python_files "$target")
    local file_count
    file_count=$(echo "$python_files" | wc -l)
    
    log "INFO" "Python files: $file_count"
    
    # Count lines
    if [[ $file_count -gt 0 ]]; then
        local line_stats
        line_stats=$(echo "$python_files" | xargs wc -l | tail -n 1)
        log "INFO" "Total lines: $(echo "$line_stats" | awk '{print $1}')"
        
        # Count imports
        local import_count
        import_count=$(echo "$python_files" | xargs grep -E "^(import|from)" | wc -l)
        log "INFO" "Import statements: $import_count"
        
        # Count functions
        local function_count
        function_count=$(echo "$python_files" | xargs grep -E "^def " | wc -l)
        log "INFO" "Function definitions: $function_count"
        
        # Count classes
        local class_count
        class_count=$(echo "$python_files" | xargs grep -E "^class " | wc -l)
        log "INFO" "Class definitions: $class_count"
    fi
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Code Formatting and Quality Script

USAGE:
    $0 [OPTIONS] [TARGET]

OPTIONS:
    -h, --help              Show this help message
    -c, --check             Check only mode (no changes will be made)
    -f, --fix               Auto-fix issues where possible
    --black-only            Run Black formatter only
    --ruff-only             Run Ruff linter only
    --mypy-only             Run MyPy type checker only
    --no-black              Skip Black formatter
    --no-ruff               Skip Ruff linter
    --no-mypy               Skip MyPy type checker
    --strict                Use strict type checking mode
    --diff                  Show diffs for formatting changes
    --report                Generate code quality report
    --stats                 Show code statistics
    --stats-only            Show statistics only, don't run tools

ARGUMENTS:
    TARGET                  File or directory to format (default: app/)

TOOL DESCRIPTIONS:
    Black                   Code formatter for consistent style
    Ruff                    Fast Python linter and formatter
    MyPy                    Static type checker

EXAMPLES:
    $0                      # Format entire app/ directory
    $0 app/core/            # Format specific directory
    $0 main.py              # Format specific file
    $0 -c                   # Check formatting without making changes
    $0 -f                   # Fix all auto-fixable issues
    $0 --black-only app/    # Run only Black formatter
    $0 --strict             # Use strict type checking
    $0 --report            # Generate detailed quality report
    $0 --stats-only        # Show code statistics only

EXIT CODES:
    0                       All checks passed
    1                       Script error or tool not found
    2                       Black formatting issues found
    4                       Ruff linting issues found  
    8                       MyPy type issues found
    
    Note: Exit codes are combined (bitwise OR) when multiple tools fail.

CONFIGURATION:
    Tools use their respective configuration files:
    - Black: pyproject.toml or command-line options
    - Ruff: pyproject.toml or ruff.toml
    - MyPy: mypy.ini or pyproject.toml

EOF
}

# Main function
main() {
    local target="app/"
    local check_only=false
    local fix_mode=false
    local run_black=true
    local run_ruff=true
    local run_mypy=true
    local strict_mode=false
    local diff_only=false
    local generate_report_flag=false
    local show_stats_flag=false
    local stats_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--check)
                check_only=true
                ;;
            -f|--fix)
                fix_mode=true
                ;;
            --black-only)
                run_ruff=false
                run_mypy=false
                ;;
            --ruff-only)
                run_black=false
                run_mypy=false
                ;;
            --mypy-only)
                run_black=false
                run_ruff=false
                ;;
            --no-black)
                run_black=false
                ;;
            --no-ruff)
                run_ruff=false
                ;;
            --no-mypy)
                run_mypy=false
                ;;
            --strict)
                strict_mode=true
                ;;
            --diff)
                diff_only=true
                ;;
            --report)
                generate_report_flag=true
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
                target="$1"
                ;;
        esac
        shift
    done
    
    # Validate target path
    if [[ ! -e "$target" ]]; then
        # Try relative to project root
        local full_target="${PROJECT_ROOT}/$target"
        if [[ -e "$full_target" ]]; then
            target="$full_target"
        else
            log "ERROR" "Target path does not exist: $target"
            exit 1
        fi
    fi
    
    # Handle stats-only mode
    if [[ "$stats_only" == true ]]; then
        show_stats "$target"
        exit 0
    fi
    
    log "INFO" "Starting code formatting and quality script..."
    log "INFO" "Project root: $PROJECT_ROOT"
    log "INFO" "Target: $target"
    
    if [[ "$check_only" == true ]]; then
        log "INFO" "Mode: Check only (no changes will be made)"
    elif [[ "$fix_mode" == true ]]; then
        log "INFO" "Mode: Fix (auto-fix issues where possible)"
    else
        log "INFO" "Mode: Format (apply formatting changes)"
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Check tool availability
    check_tools
    
    # Show statistics if requested
    if [[ "$show_stats_flag" == true ]]; then
        show_stats "$target"
    fi
    
    # Track exit codes
    local overall_exit_code=0
    
    # Run Black formatter
    if [[ "$run_black" == true ]]; then
        local black_exit_code=0
        run_black "$target" "$check_only" "$diff_only" || black_exit_code=$?
        if [[ $black_exit_code -ne 0 ]]; then
            overall_exit_code=$((overall_exit_code | 2))
        fi
    fi
    
    # Run Ruff linter
    if [[ "$run_ruff" == true ]]; then
        local ruff_exit_code=0
        run_ruff "$target" "$check_only" "$fix_mode" || ruff_exit_code=$?
        if [[ $ruff_exit_code -ne 0 ]]; then
            overall_exit_code=$((overall_exit_code | 4))
        fi
        
        # Also run Ruff format if not running Black
        if [[ "$run_black" != true ]]; then
            run_ruff_format "$target" "$check_only" "$diff_only" || {
                local ruff_format_exit_code=$?
                if [[ $ruff_format_exit_code -ne 0 ]]; then
                    overall_exit_code=$((overall_exit_code | 4))
                fi
            }
        fi
    fi
    
    # Run MyPy type checker
    if [[ "$run_mypy" == true ]]; then
        local mypy_exit_code=0
        run_mypy "$target" "$strict_mode" || mypy_exit_code=$?
        if [[ $mypy_exit_code -ne 0 ]]; then
            overall_exit_code=$((overall_exit_code | 8))
        fi
    fi
    
    # Generate report if requested
    if [[ "$generate_report_flag" == true ]]; then
        generate_report "$target"
    fi
    
    # Final status
    if [[ $overall_exit_code -eq 0 ]]; then
        log "SUCCESS" "All code quality checks passed"
    else
        log "WARN" "Some code quality issues found (exit code: $overall_exit_code)"
        
        # Decode exit code
        if [[ $((overall_exit_code & 2)) -ne 0 ]]; then
            log "WARN" "  - Black formatting issues"
        fi
        if [[ $((overall_exit_code & 4)) -ne 0 ]]; then
            log "WARN" "  - Ruff linting issues"
        fi
        if [[ $((overall_exit_code & 8)) -ne 0 ]]; then
            log "WARN" "  - MyPy type checking issues"
        fi
        
        if [[ "$check_only" == true ]]; then
            log "INFO" "Run without --check to apply automatic fixes"
        elif [[ "$fix_mode" != true ]]; then
            log "INFO" "Run with --fix to apply automatic fixes"
        fi
    fi
    
    log "INFO" "Code formatting and quality script completed"
    exit $overall_exit_code
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"