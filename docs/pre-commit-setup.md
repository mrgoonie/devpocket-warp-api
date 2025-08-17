# Pre-commit Hook Setup Guide

This guide explains how to install and use the pre-commit framework with the DevPocket API project to automatically run Black formatting and other code quality checks before each commit.

## Overview

The pre-commit framework automatically runs configured tools (formatters, linters, security scanners) on your code before each commit. This ensures consistent code quality and prevents common issues from being committed to the repository.

### Configured Hooks

The project includes the following pre-commit hooks:

#### Code Formatting & Quality
- **Black**: Python code formatter (primary formatter)
- **Ruff**: Fast Python linter and secondary formatter
- **Bandit**: Security vulnerability scanner

#### File Quality Checks
- **Trailing whitespace removal**
- **End-of-file fixer**
- **Mixed line ending fixes**
- **Python AST syntax validation**
- **Debug statement detection**

#### General File Checks
- **Large file detection** (max 500KB)
- **Case conflict detection**
- **Merge conflict marker detection**
- **YAML/JSON/TOML syntax validation**

## Installation

### Prerequisites

1. **Python 3.11+** installed
2. **Git repository** initialized
3. **Virtual environment** recommended

### Step 1: Install Development Dependencies

Install the development requirements which include pre-commit:

```bash
# Using pip
pip install -r requirements-dev.txt

# Or install just pre-commit
pip install pre-commit==3.6.0
```

### Step 2: Install Pre-commit Hooks

Install the git hooks in your repository:

```bash
# Install hooks for this repository
pre-commit install

# Optional: Install hooks for commit messages
pre-commit install --hook-type commit-msg

# Optional: Install hooks for pre-push
pre-commit install --hook-type pre-push
```

You should see output like:
```
pre-commit installed at .git/hooks/pre-commit
```

### Step 3: Verify Installation

Test that the hooks are working:

```bash
# Run hooks on all files (first time setup)
pre-commit run --all-files

# Run hooks on staged files only
pre-commit run
```

## Usage

### Automatic Hook Execution

Once installed, pre-commit hooks run automatically when you commit:

```bash
git add .
git commit -m "feat: add new feature"
# Hooks will run automatically here
```

If any hook fails, the commit will be aborted and you'll see output showing what needs to be fixed.

### Manual Hook Execution

You can run hooks manually without committing:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run all hooks on staged files
pre-commit run

# Run specific hook on all files
pre-commit run black --all-files
pre-commit run ruff --all-files

# Run specific hook on specific files
pre-commit run black --files app/core/auth.py
```

### Hook Configuration

The hooks are configured in `.pre-commit-config.yaml`. Key settings:

#### Black Configuration
- **Line length**: 88 characters
- **Target Python version**: 3.11
- **Excludes**: `migrations/` directory
- **File types**: Python files only

#### Ruff Configuration
- **Linting with auto-fix**: Enabled
- **Formatting**: Secondary to Black
- **Excludes**: `migrations/` directory

#### Security Scanning
- **Bandit**: Checks for common security issues
- **Skips**: Assert statements and paramiko usage (expected in our use case)

## Integration with Existing Scripts

The pre-commit hooks are designed to work alongside the existing `scripts/format_code.sh` script:

### format_code.sh vs Pre-commit

| Feature | format_code.sh | Pre-commit |
|---------|----------------|------------|
| **When it runs** | Manual execution | Automatic on commit |
| **Scope** | Full project or specified paths | Only changed files |
| **Tools** | Black, Ruff, MyPy | Black, Ruff, Bandit, file checks |
| **Configuration** | Command-line args | .pre-commit-config.yaml |
| **Speed** | Slower (full analysis) | Faster (changed files only) |
| **Use case** | Development, CI/CD | Commit-time validation |

### Recommended Workflow

1. **During development**: Use `scripts/format_code.sh` for comprehensive checking
2. **Before committing**: Pre-commit hooks run automatically
3. **In CI/CD**: Use `scripts/format_code.sh` for full validation

## Troubleshooting

### Hook Execution Issues

If hooks fail to run or behave unexpectedly:

```bash
# Update hooks to latest versions
pre-commit autoupdate

# Clean and reinstall hooks
pre-commit uninstall
pre-commit install

# Clear pre-commit cache
pre-commit clean
```

### Bypassing Hooks (Emergency)

**⚠️ Use sparingly and only in emergencies:**

```bash
# Skip all hooks for one commit
git commit --no-verify -m "emergency fix"

# Skip specific hook
SKIP=black git commit -m "skip black for this commit"

# Skip multiple hooks
SKIP=black,ruff git commit -m "skip formatting for this commit"
```

### Common Issues and Solutions

#### 1. "Pre-commit command not found"
```bash
# Ensure pre-commit is installed
pip install pre-commit

# Check installation
pre-commit --version
```

#### 2. "Hook execution failed"
```bash
# Run hooks manually to see detailed errors
pre-commit run --all-files --verbose

# Check specific hook
pre-commit run black --files problematic_file.py --verbose
```

#### 3. "Black formatting conflicts with editor"
Ensure your editor's Python formatter is set to Black with the same configuration:
- Line length: 88
- Target version: py311

#### 4. "Hooks are too slow"
```bash
# Run only fast hooks
SKIP=bandit,mypy git commit -m "skip slow hooks"

# Or configure editor to format on save instead
```

## Configuration Customization

### Modifying Hook Behavior

Edit `.pre-commit-config.yaml` to customize hooks:

```yaml
# Example: Change Black line length
- repo: https://github.com/psf/black
  rev: 23.11.0
  hooks:
    - id: black
      args: [--line-length=100]  # Changed from 88
```

### Adding New Hooks

Add new tools to `.pre-commit-config.yaml`:

```yaml
# Example: Add docstring formatter
- repo: https://github.com/PyCQA/docformatter
  rev: v1.7.5
  hooks:
    - id: docformatter
      args: [--in-place, --wrap-summaries=88]
```

### Repository-specific Configuration

Hooks can be configured per repository in `.pre-commit-config.yaml` or globally:

```bash
# Install hooks globally (for all repositories)
pre-commit install --install-hooks -g

# Configure global hooks
pre-commit install-hooks --config ~/.pre-commit-config.yaml
```

## Best Practices

### 1. Regular Updates
```bash
# Update hook versions weekly
pre-commit autoupdate
```

### 2. Consistent Configuration
- Keep `.pre-commit-config.yaml` in sync with `pyproject.toml`
- Match tool versions with `requirements-dev.txt`

### 3. Team Workflow
- All team members should install pre-commit hooks
- Include installation instructions in project README
- Consider adding pre-commit installation to setup scripts

### 4. CI/CD Integration
```bash
# In CI, run pre-commit on all files
pre-commit run --all-files --show-diff-on-failure
```

## Integration with IDEs

### VS Code
Add to `.vscode/settings.json`:
```json
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "editor.formatOnSave": true
}
```

### PyCharm
1. Install Black plugin
2. Configure Black in Settings → Tools → Black
3. Set line length to 88
4. Enable format on save

## Performance Optimization

### File Caching
Pre-commit automatically caches file states and tool installations. To manage cache:

```bash
# View cache location
pre-commit cache dir

# Clean cache
pre-commit clean

# Clean specific cache
pre-commit clean --repo https://github.com/psf/black
```

### Selective Hook Execution
For large repositories, consider running different hooks based on file changes:

```yaml
# Example: Only run Black on Python files in app/
- repo: https://github.com/psf/black
  rev: 23.11.0
  hooks:
    - id: black
      files: ^app/.*\.py$
```

## Monitoring and Metrics

### Hook Performance
```bash
# Show hook execution times
pre-commit run --all-files --verbose

# Profile hook performance
time pre-commit run --all-files
```

### Code Quality Metrics
Track improvements over time:
- Number of formatting issues caught
- Security vulnerabilities prevented
- Consistency of code style across team

## Related Documentation

- [Code Style Guide](./code-style-guide.md)
- [Development Setup](./development-setup.md)
- [Testing Guide](../TESTING.md)
- [Contributing Guidelines](../CONTRIBUTING.md)

## Support

For issues with pre-commit setup:
1. Check this documentation
2. Review hook configuration in `.pre-commit-config.yaml`
3. Test with `scripts/format_code.sh` for comparison
4. Consult pre-commit documentation: https://pre-commit.com/