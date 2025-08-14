# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DevPocket is an AI-powered mobile terminal application that brings command-line functionality to mobile devices. The project consists of a FastAPI backend server (planned) and Flutter mobile application (planned), with documentation currently in the `docs/` directory.

Key features:
- **BYOK (Bring Your Own Key)** model for AI features using OpenRouter
- SSH connections with PTY support for remote server access
- Local terminal emulation on mobile devices
- Natural language to command conversion using AI
- WebSocket-based real-time terminal communication
- Multi-device synchronization

## Architecture

### Backend (FastAPI - Python)
The backend implementation is documented in `docs/devpocket-server-implementation-py.md`:

- **WebSocket Terminal**: Real-time terminal communication at `/ws/terminal`
- **SSH/PTY Support**: Direct terminal interaction with pseudo-terminal support
- **AI Service**: BYOK model where users provide their own OpenRouter API keys
- **Authentication**: JWT-based authentication system
- **Database**: PostgreSQL for persistent storage, Redis for caching
- **Connection Management**: WebSocket connection manager for real-time updates

### Frontend (Flutter - Dart)
The mobile app structure is documented in:
- `docs/devpocket-flutter-app-structure-dart.md` - App architecture
- `docs/devpocket-flutter-implementation-dart.md` - Implementation details
- `docs/devpocket-flutter-integration.md` - Backend integration

### API Endpoints
Complete API specification in `docs/devpocket-api-endpoints.md`:
- Authentication endpoints (`/api/auth/*`)
- Terminal operations (`/api/ssh/*`, `/api/commands/*`)
- AI features (`/api/ai/*`) - all using BYOK model
- Synchronization (`/api/sync/*`)
- WebSocket terminal (`/ws/terminal`)

## Development Commands

Since this is currently a documentation-only repository with planned implementation:

### Future Backend Commands (Python/FastAPI)
```bash
# Install dependencies (when implemented)
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Database migrations
alembic upgrade head

# Format code
black .
ruff check --fix .
```

### Future Frontend Commands (Flutter)
```bash
# Install dependencies
flutter pub get

# Run on iOS simulator
flutter run -d ios

# Run on Android
flutter run -d android

# Build for production
flutter build ios
flutter build apk
```

## Key Implementation Notes

### BYOK (Bring Your Own Key) Model
- Users provide their own OpenRouter API keys
- No API costs for the service provider
- Higher gross margins (85-98%)
- API keys are never stored, only validated

### Security Considerations
- JWT tokens for authentication
- SSH keys handled securely
- API keys transmitted but never stored
- WebSocket connections authenticated via token

### Real-time Features
- WebSocket for terminal I/O streaming
- PTY support for interactive terminal sessions
- Multi-device synchronization via Redis pub/sub

## Business Model

Freemium tiers documented in `docs/devpocket-product-overview.md`:
- **Free Tier**: Core terminal + BYOK AI features
- **Pro Tier ($12/mo)**: Multi-device sync, cloud history, AI caching
- **Team Tier ($25/user/mo)**: Team workspaces, shared workflows, SSO

## Testing Approach

When implementation begins:
- Unit tests for all core services
- Integration tests for API endpoints
- WebSocket connection tests
- Mock OpenRouter API for AI service tests
- Flutter widget tests for UI components