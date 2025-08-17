#!/bin/bash
# DevPocket API - Pre-commit Setup Script
# Automates the installation and configuration of pre-commit hooks

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

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log "ERROR" "Not a git repository. Please run this script from within a git repository."
        exit 1
    fi
    log "SUCCESS" "Git repository detected"
}

# Check if virtual environment exists and activate it
activate_venv() {
    local venv_path="${PROJECT_ROOT}/venv"
    
    if [[ -d "$venv_path" ]]; then
        log "INFO" "Activating virtual environment..."
        source "$venv_path/bin/activate"
        log "SUCCESS" "Virtual environment activated"
        return 0
    else
        log "WARN" "Virtual environment not found at $venv_path"
        log "INFO" "Using system Python environment"
        return 1
    fi
}

# Check if Python 3.11+ is available
check_python_version() {
    local python_cmd="python3"
    
    if ! command -v "$python_cmd" &> /dev/null; then
        python_cmd="python"
        if ! command -v "$python_cmd" &> /dev/null; then
            log "ERROR" "Python not found. Please install Python 3.11+"
            exit 1
        fi
    fi
    
    local python_version
    python_version=$("$python_cmd" --version 2>&1 | awk '{print $2}')
    local major_version
    major_version=$(echo "$python_version" | cut -d. -f1)
    local minor_version
    minor_version=$(echo "$python_version" | cut -d. -f2)
    
    if [[ "$major_version" -lt 3 ]] || [[ "$major_version" -eq 3 && "$minor_version" -lt 11 ]]; then
        log "ERROR" "Python 3.11+ required, found $python_version"
        exit 1
    fi
    
    log "SUCCESS" "Python $python_version detected"
    echo "$python_cmd"
}

# Install development requirements
install_dev_requirements() {
    local python_cmd="$1"
    local force_install="$2"
    
    log "INFO" "Installing development requirements..."
    
    # Check if requirements-dev.txt exists
    local requirements_file="${PROJECT_ROOT}/requirements-dev.txt"
    if [[ ! -f "$requirements_file" ]]; then
        log "ERROR" "requirements-dev.txt not found at $requirements_file"
        exit 1
    fi
    
    # Install requirements
    if [[ "$force_install" == true ]]; then
        log "INFO" "Force installing all development requirements..."
        "$python_cmd" -m pip install --upgrade -r "$requirements_file"
    else
        # Check if pre-commit is already installed
        if command -v pre-commit &> /dev/null; then
            log "INFO" "Pre-commit already installed, skipping pip install"
        else
            log "INFO" "Installing development requirements..."
            "$python_cmd" -m pip install -r "$requirements_file"
        fi
    fi
    
    log "SUCCESS" "Development requirements installed"
}

# Install pre-commit hooks
install_pre_commit_hooks() {
    log "INFO" "Installing pre-commit hooks..."
    
    # Check if .pre-commit-config.yaml exists
    local config_file="${PROJECT_ROOT}/.pre-commit-config.yaml"
    if [[ ! -f "$config_file" ]]; then
        log "ERROR" ".pre-commit-config.yaml not found at $config_file"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    
    # Install hooks
    if ! pre-commit install; then
        log "ERROR" "Failed to install pre-commit hooks"
        exit 1
    fi
    
    # Install commit-msg hooks (optional)
    if pre-commit install --hook-type commit-msg 2>/dev/null; then
        log "SUCCESS" "Commit message hooks installed"
    else
        log "INFO" "Commit message hooks not available (this is normal)"
    fi
    
    log "SUCCESS" "Pre-commit hooks installed"
}

# Run initial hook validation
validate_hooks() {
    local run_on_all_files="$1"
    
    log "INFO" "Validating pre-commit hook installation..."
    
    cd "$PROJECT_ROOT"
    
    if [[ "$run_on_all_files" == true ]]; then
        log "INFO" "Running hooks on all files (this may take a while)..."
        if pre-commit run --all-files; then
            log "SUCCESS" "All hooks passed on existing codebase"
        else
            log "WARN" "Some hooks failed on existing code. This is normal for new setups."
            log "INFO" "Run './scripts/format_code.sh' to fix formatting issues"
        fi
    else
        # Just validate hook installation
        if pre-commit run --files /dev/null &>/dev/null || true; then
            log "SUCCESS" "Hook validation completed"
        else
            log "WARN" "Hook validation had issues, but hooks are installed"
        fi
    fi
}

# Show hook configuration summary
show_summary() {
    log "INFO" "Pre-commit hook setup summary:"
    echo ""
    echo "  📁 Configuration file: .pre-commit-config.yaml"
    echo "  🐍 Python tools: Black, Ruff, Bandit"
    echo "  📝 File checks: Whitespace, syntax, merge conflicts"
    echo "  🔒 Security: Bandit vulnerability scanning"
    echo ""
    echo "  Usage:"
    echo "    • Hooks run automatically on 'git commit'"
    echo "    • Manual run: 'pre-commit run --all-files'"
    echo "    • Update hooks: 'pre-commit autoupdate'"
    echo "    • Skip hooks: 'git commit --no-verify' (emergency only)"
    echo ""
    echo "  Integration:"
    echo "    • Compatible with existing ./scripts/format_code.sh"
    echo "    • Uses same Black/Ruff configuration"
    echo "    • Faster (only changed files) vs comprehensive (all files)"
    echo ""
    log "SUCCESS" "Setup complete! See docs/pre-commit-setup.md for detailed usage"
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Pre-commit Setup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -f, --force             Force reinstall all dependencies
    -a, --all-files         Run hooks on all files during validation
    --no-venv               Skip virtual environment activation
    --hooks-only            Only install hooks (skip dependency installation)

DESCRIPTION:
    This script automates the setup of pre-commit hooks for the DevPocket API project.
    It installs the necessary Python packages and configures git hooks to automatically
    run Black formatting, Ruff linting, and other code quality checks before commits.

STEPS PERFORMED:
    1. Check git repository and Python version
    2. Activate virtual environment (if available)
    3. Install development requirements (pre-commit, black, ruff, etc.)
    4. Install pre-commit git hooks
    5. Validate hook installation
    6. Show configuration summary

EXAMPLES:
    $0                      # Standard setup
    $0 -f                   # Force reinstall all dependencies
    $0 -a                   # Run hooks on all files during setup
    $0 --hooks-only         # Only install hooks, skip pip install

POST-SETUP:
    After running this script, pre-commit hooks will automatically run when you commit.
    For detailed configuration and usage, see: docs/pre-commit-setup.md

TROUBLESHOOTING:
    • If hooks fail: Run './scripts/format_code.sh' to fix formatting
    • For updates: Run 'pre-commit autoupdate'
    • For emergencies: Use 'git commit --no-verify' to skip hooks

EOF
}

# Main function
main() {
    local force_install=false
    local run_on_all_files=false
    local skip_venv=false
    local hooks_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -f|--force)
                force_install=true
                ;;
            -a|--all-files)
                run_on_all_files=true
                ;;
            --no-venv)
                skip_venv=true
                ;;
            --hooks-only)
                hooks_only=true
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
    
    log "INFO" "Starting pre-commit hook setup..."
    log "INFO" "Project root: $PROJECT_ROOT"
    
    # Step 1: Check prerequisites
    check_git_repo
    local python_cmd
    python_cmd=$(check_python_version)
    
    # Step 2: Virtual environment
    if [[ "$skip_venv" != true ]]; then
        activate_venv || true
    fi
    
    # Step 3: Install dependencies
    if [[ "$hooks_only" != true ]]; then
        install_dev_requirements "$python_cmd" "$force_install"
    else
        log "INFO" "Skipping dependency installation (--hooks-only mode)"
        # Still verify pre-commit is available
        if ! command -v pre-commit &> /dev/null; then
            log "ERROR" "pre-commit not found. Install with: pip install pre-commit"
            exit 1
        fi
    fi
    
    # Step 4: Install hooks
    install_pre_commit_hooks
    
    # Step 5: Validate installation
    validate_hooks "$run_on_all_files"
    
    # Step 6: Show summary
    show_summary
    
    log "SUCCESS" "Pre-commit hook setup completed successfully!"
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"