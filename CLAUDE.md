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
- **Free Tier (7 days)**: Core terminal + BYOK AI features
- **Pro Tier ($12/mo)**: Multi-device sync, cloud history, AI caching
- **Team Tier ($25/user/mo)**: Team workspaces, shared workflows, SSO

## Testing Approach

When implementation begins:
- Unit tests for all core services
- Integration tests for API endpoints
- WebSocket connection tests
- Mock OpenRouter API for AI service tests
- Flutter widget tests for UI components

## Development Rules

### Environment Setup
- Use docker compose for development environment

### Code Quality Guidelines
- Don't be too harsh on code linting and formatting
- Prioritize functionality and readability over strict style enforcement
- Use reasonable code quality standards that enhance developer productivity
- Allow for minor style variations when they improve code clarity

### Pre-commit/Push Rules
- Run `./scripts/format_code.sh` before commit
- Run `./scripts/run_tests.sh` before push
