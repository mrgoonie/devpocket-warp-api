# DevPocket API Backend

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io)
[![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-yellow.svg)](https://fastapi.tiangolo.com/advanced/websockets/)

**DevPocket** is an AI-powered mobile terminal application that brings command-line functionality to mobile devices. This FastAPI backend provides real-time terminal communication, SSH connections, and AI-powered command assistance using a BYOK (Bring Your Own Key) model.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+**
- **Redis 7+**
- **Git**

### Local Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd devpocket-warp-api
```

2. **Run setup script**
```bash
python setup.py
```

This will:
- Create and activate a virtual environment
- Install all dependencies
- Set up environment configuration
- Initialize the database
- Run initial migrations

3. **Start development server**
```bash
./scripts/dev_start.sh
```

The API will be available at `http://localhost:8000`

### Docker Installation

1. **Development environment**
```bash
docker-compose up -d
```

2. **Production environment**
```bash
docker-compose -f docker-compose.prod.yaml up -d
```

## 📚 API Documentation

- **Interactive API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative API Docs**: `http://localhost:8000/redoc` (ReDoc)
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Key Endpoints

#### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/refresh` - Token refresh
- `GET /api/auth/me` - Current user info

#### Terminal Sessions
- `POST /api/sessions` - Create terminal session
- `GET /api/sessions` - List user sessions
- `WebSocket /ws/terminal` - Real-time terminal

#### SSH Management
- `POST /api/ssh/profiles` - Create SSH profile
- `GET /api/ssh/profiles` - List SSH profiles
- `POST /api/ssh/profiles/{id}/test` - Test SSH connection

#### AI Services (BYOK)
- `POST /api/ai/suggest-command` - Natural language to command
- `POST /api/ai/explain-command` - Command explanation
- `POST /api/ai/explain-error` - Error analysis

## 🏗️ Architecture

### Core Technologies
- **FastAPI**: Modern Python web framework with automatic OpenAPI docs
- **SQLAlchemy**: ORM with repository pattern for database operations
- **Alembic**: Database migration management
- **JWT**: Token-based authentication with refresh mechanism
- **WebSocket**: Real-time terminal communication
- **PostgreSQL**: Primary database for persistent storage
- **Redis**: Caching and session management
- **PTY**: Pseudo-terminal support for interactive applications

### Key Features
- **Real-time Terminal**: WebSocket-based terminal with PTY support
- **SSH Integration**: Secure remote server connections
- **AI-Powered**: Command suggestions and error explanations via OpenRouter
- **BYOK Model**: Users provide their own API keys (no storage)
- **Multi-device Sync**: Cross-device command history and settings
- **Security First**: JWT auth, rate limiting, input validation

## 🛠️ Development

### Project Structure
```
devpocket-warp-api/
├── app/                    # Main application code
│   ├── api/               # REST API endpoints
│   ├── auth/              # Authentication system
│   ├── core/              # Core configuration
│   ├── db/                # Database connection
│   ├── middleware/        # FastAPI middleware
│   ├── models/            # SQLAlchemy models
│   ├── repositories/      # Repository pattern
│   ├── services/          # Business logic
│   └── websocket/         # WebSocket handlers
├── migrations/            # Alembic database migrations
├── tests/                 # Comprehensive test suite
├── scripts/              # Utility scripts
├── docs/                 # Project documentation
└── docker-compose.yaml   # Development environment
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/devpocket_warp_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# API Configuration
API_V1_STR=/api
PROJECT_NAME=DevPocket API
DEBUG=true
```

### Database Operations

```bash
# Run migrations
./scripts/db_migrate.sh

# Seed sample data
./scripts/db_seed.sh

# Reset database (development)
./scripts/db_reset.sh
```

### Testing

```bash
# Run all tests with coverage
./scripts/run_tests.sh

# Run specific test modules
pytest tests/test_auth/
pytest tests/test_api/test_ssh_endpoints.py
```

### Code Quality

```bash
# Format code and run linting
./scripts/format_code.sh

# This runs:
# - black (code formatting)
# - ruff (linting with fixes)
# - mypy (type checking)
```

## 🐳 Docker Deployment

### Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Execute commands in container
docker-compose exec api bash
```

### Production
```bash
# Build and start production services
docker-compose -f docker-compose.prod.yaml up -d

# Scale API service
docker-compose -f docker-compose.prod.yaml up -d --scale api=3
```

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: API rate limiting by subscription tier
- **Input Validation**: Comprehensive request validation
- **CORS Configuration**: Secure cross-origin resource sharing
- **Security Headers**: HSTS, CSP, XSS protection
- **SQL Injection Protection**: Parameterized queries
- **BYOK Model**: No API key storage for external services

## 🚀 Production Deployment

### Environment Setup

1. **Database**: PostgreSQL with connection pooling
2. **Cache**: Redis with persistence
3. **Web Server**: Gunicorn with multiple workers
4. **Reverse Proxy**: Nginx (recommended)
5. **HTTPS**: SSL/TLS termination
6. **Monitoring**: Health checks and logging

### Production Checklist

- [ ] Set strong JWT secret keys
- [ ] Configure PostgreSQL with SSL
- [ ] Set up Redis with authentication
- [ ] Enable HTTPS with valid certificates
- [ ] Configure CORS for your domain
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up database backups
- [ ] Configure rate limiting
- [ ] Review security headers

## 📊 WebSocket Protocol

The real-time terminal uses a JSON-based WebSocket protocol:

### Connection
```javascript
// Connect with JWT token
ws://localhost:8000/ws/terminal?token=your_jwt_token
```

### Message Types
```json
// Terminal input
{
  "type": "input",
  "session_id": "uuid",
  "data": "ls -la",
  "timestamp": "2024-01-15T10:30:00Z"
}

// Terminal output
{
  "type": "output", 
  "session_id": "uuid",
  "data": "total 48\ndrwxr-xr-x 12 user user 4096 Jan 15 10:30 .\n",
  "timestamp": "2024-01-15T10:30:01Z"
}

// Terminal resize
{
  "type": "resize",
  "session_id": "uuid", 
  "data": {"rows": 24, "cols": 80}
}

// Session control
{
  "type": "connect",
  "data": {
    "session_type": "ssh",
    "ssh_profile_id": "uuid"
  }
}
```

## 🤖 AI Integration (BYOK)

DevPocket uses a Bring Your Own Key model for AI features:

1. **Get OpenRouter API Key**: Sign up at [OpenRouter.ai](https://openrouter.ai)
2. **Validate Key**: Use `POST /api/ai/validate-key` endpoint
3. **Use AI Features**: All AI endpoints require the API key in requests
4. **No Storage**: API keys are never stored on our servers

### Supported AI Features
- Natural language to command conversion
- Command explanation and documentation  
- Error message analysis and solutions
- Command optimization suggestions

## 📈 Monitoring & Health Checks

### Health Endpoints
- `GET /health` - Application health status
- `GET /health/db` - Database connectivity  
- `GET /health/redis` - Redis connectivity
- `GET /metrics` - Application metrics (Prometheus format)

### Logging
Structured JSON logging with configurable levels:
- Application logs: `/logs/app.log`
- Access logs: `/logs/access.log`
- Error logs: `/logs/error.log`

## 🧪 Testing

The project includes comprehensive testing:

- **Unit Tests**: 80%+ coverage requirement
- **Integration Tests**: End-to-end API workflows
- **WebSocket Tests**: Real-time communication
- **Security Tests**: Input validation and auth
- **Performance Tests**: Load and stress testing

```bash
# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test categories  
pytest -m "not slow"  # Skip slow tests
pytest -m "security"  # Security tests only
```

## 📝 API Rate Limits

Rate limiting by subscription tier:

| Tier       | General | Auth | AI Features |
|------------|---------|------|-------------|
| Free       | 60/min  | 10/min | 10/day     |
| Pro        | 300/min | 20/min | 100/day    |
| Team       | 1000/min| 50/min | 500/day    |
| Enterprise | 5000/min| 100/min| Unlimited  |

## 🔄 Database Schema

Key entities and relationships:

- **Users**: Authentication and subscription management
- **Sessions**: Terminal session tracking
- **Commands**: Command execution history
- **SSH Profiles**: Remote server configurations  
- **SSH Keys**: Encrypted key storage
- **Sync Data**: Cross-device synchronization

## 🛠️ Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql
# Verify connection settings in .env
```

**Redis Connection Failed**
```bash
# Check Redis status  
sudo systemctl status redis
# Test connection
redis-cli ping
```

**WebSocket Connection Issues**
- Verify JWT token is valid and not expired
- Check CORS configuration for your domain
- Ensure WebSocket endpoint is accessible

**Performance Issues**
- Enable connection pooling for database
- Configure Redis caching appropriately
- Use Gunicorn with multiple workers in production
- Monitor memory usage and optimize queries

### Getting Help

1. Check the [API documentation](http://localhost:8000/docs)
2. Review application logs in `/logs/`  
3. Run health checks at `/health`
4. Check GitHub issues for known problems
5. Submit bug reports with logs and reproduction steps

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `./scripts/run_tests.sh`
5. Format code: `./scripts/format_code.sh`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure 80%+ test coverage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- SQLAlchemy for robust ORM capabilities  
- OpenRouter for AI API aggregation
- Alembic for database migration management
- pytest for comprehensive testing framework