# DevPocket Project Overview

## Purpose
DevPocket is an AI-powered mobile terminal application that brings command-line functionality to mobile devices. It consists of a FastAPI backend server and Flutter mobile application with focus on SSH connections, PTY support, and AI-powered command assistance using a BYOK (Bring Your Own Key) model.

## Tech Stack
- **Backend**: FastAPI (Python) with async/await support
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM and Alembic migrations
- **Cache**: Redis for caching and pub/sub
- **Authentication**: JWT tokens with bcrypt password hashing
- **WebSocket**: Real-time terminal communication
- **SSH**: Paramiko for SSH connections and pexpect for PTY support
- **AI**: OpenRouter API integration (BYOK model)
- **Testing**: pytest with async support

## Key Features
- JWT-based authentication system
- SSH connections with PTY support
- WebSocket terminal communication
- AI command suggestions and explanations (BYOK)
- Multi-device synchronization
- Freemium subscription model (Free/Pro/Team/Enterprise)

## Database Layer Status
- Complete SQLAlchemy models with proper relationships
- User model with authentication fields (password_hash, failed_login_attempts, etc.)
- Repository pattern implemented
- Alembic migrations configured
- Database connection management ready

## Current Implementation Status
- Database layer: ✅ Complete
- Authentication system: ❌ Not implemented (current task)
- API endpoints: ❌ Not implemented
- WebSocket terminal: ❌ Not implemented
- AI integration: ❌ Not implemented