# DevPocket Development Commands

## Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Edit with your database/redis credentials
```

## Database Commands
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Downgrade migration
alembic downgrade -1
```

## Development Server
```bash
# Run development server with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run with specific log level
uvicorn main:app --reload --log-level debug
```

## Code Quality & Testing
```bash
# Format code
black .

# Lint with ruff
ruff check --fix .

# Type checking
mypy .

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

## Git Commands (Linux)
```bash
# Standard git operations
git status
git add .
git commit -m "message"
git push origin main

# View logs
git log --oneline -10
```

## System Commands (Linux)
```bash
# File operations
ls -la
find . -name "*.py" -type f
grep -r "pattern" --include="*.py" .

# Process management
ps aux | grep uvicorn
pkill -f uvicorn
```

## Development Workflow
1. Make code changes
2. Run `black .` to format
3. Run `ruff check --fix .` to lint
4. Run `pytest` to test
5. Commit changes with conventional commit format