#!/bin/bash
# DevPocket API - Database Seeding Script
# Seeds database with sample data using existing factories

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

# Check database connection
check_database() {
    log "INFO" "Checking database connection..."
    
    if python "${SCRIPT_DIR}/db_utils.py" test; then
        log "SUCCESS" "Database connection verified"
    else
        log "ERROR" "Database connection failed"
        log "INFO" "Please ensure PostgreSQL is running and migrations are up to date"
        exit 1
    fi
}

# Clean specific data types from database
clean_data() {
    local data_types="$1"
    local force_clean="$2"
    
    log "INFO" "Cleaning data types: $data_types"
    
    # Create temporary cleaning script
    local clean_script="${PROJECT_ROOT}/temp_clean_script.py"
    
    cat > "$clean_script" << 'EOF'
#!/usr/bin/env python3
"""
Temporary cleaning script for DevPocket API
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def clean_database(data_types: str, force_clean: bool = False):
    """Clean specific data types from database."""
    
    from app.db.database import AsyncSessionLocal
    from app.core.logging import logger
    from sqlalchemy import text
    
    # Import models
    from app.models.user import User
    from app.models.ssh_profile import SSHProfile, SSHKey
    from app.models.command import Command
    from app.models.session import Session
    from app.models.sync import SyncData
    
    logger.info(f"Starting database cleaning (types: {data_types}, force: {force_clean})")
    
    try:
        async with AsyncSessionLocal() as session:
            
            # Parse data types to clean
            types_to_clean = [t.strip() for t in data_types.split(',')]
            
            # Clean in reverse dependency order to avoid FK constraint issues
            if 'all' in types_to_clean or 'commands' in types_to_clean:
                logger.info("Cleaning commands...")
                result = await session.execute(text("DELETE FROM commands"))
                logger.info(f"Deleted {result.rowcount} commands")
            
            if 'all' in types_to_clean or 'sessions' in types_to_clean:
                logger.info("Cleaning sessions...")
                result = await session.execute(text("DELETE FROM sessions"))
                logger.info(f"Deleted {result.rowcount} sessions")
            
            if 'all' in types_to_clean or 'ssh' in types_to_clean:
                logger.info("Cleaning SSH profiles...")
                result = await session.execute(text("DELETE FROM ssh_profiles"))
                logger.info(f"Deleted {result.rowcount} SSH profiles")
                
                logger.info("Cleaning SSH keys...")
                result = await session.execute(text("DELETE FROM ssh_keys"))
                logger.info(f"Deleted {result.rowcount} SSH keys")
            
            if 'all' in types_to_clean or 'sync' in types_to_clean:
                logger.info("Cleaning sync data...")
                result = await session.execute(text("DELETE FROM sync_data"))
                logger.info(f"Deleted {result.rowcount} sync data records")
            
            if 'all' in types_to_clean or 'settings' in types_to_clean:
                logger.info("Cleaning user settings...")
                result = await session.execute(text("DELETE FROM user_settings"))
                logger.info(f"Deleted {result.rowcount} user settings")
            
            if 'all' in types_to_clean or 'users' in types_to_clean:
                logger.info("Cleaning users...")
                result = await session.execute(text("DELETE FROM users"))
                logger.info(f"Deleted {result.rowcount} users")
            
            # Reset sequences if requested
            if force_clean:
                logger.info("Resetting database sequences...")
                await session.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), 1, false)"))
            
            await session.commit()
            logger.info("Database cleaning completed successfully")
            
    except Exception as e:
        logger.error(f"Database cleaning failed: {e}")
        raise

async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python temp_clean_script.py <data_types> [force]")
        sys.exit(1)
    
    data_types = sys.argv[1]
    force_clean = len(sys.argv) > 2 and sys.argv[2].lower() == 'true'
    
    await clean_database(data_types, force_clean)

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    # Ask for confirmation unless force is used
    if [[ "$force_clean" != "true" ]]; then
        log "WARN" "About to clean data types: $data_types"
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "INFO" "Cleaning cancelled by user"
            rm -f "$clean_script"
            return 0
        fi
    fi
    
    # Run the cleaning script
    cd "$PROJECT_ROOT"
    
    if python "$clean_script" "$data_types" "$force_clean"; then
        log "SUCCESS" "Database cleaning completed successfully"
    else
        log "ERROR" "Database cleaning failed"
        rm -f "$clean_script"
        exit 1
    fi
    
    # Clean up temporary script
    rm -f "$clean_script"
}

# Reset entire database
reset_database() {
    local force_reset="$1"
    
    log "INFO" "Resetting entire database..."
    
    if [[ "$force_reset" != "true" ]]; then
        log "WARN" "This will completely reset the database, removing ALL data"
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "INFO" "Database reset cancelled by user"
            return 0
        fi
    fi
    
    # Use db_utils.py to reset database
    if python "${SCRIPT_DIR}/db_utils.py" reset; then
        log "SUCCESS" "Database reset completed successfully"
    else
        log "ERROR" "Database reset failed"
        exit 1
    fi
}

# Create seeding script and run it
run_seeding() {
    local seed_type="$1"
    local count="$2"
    local use_upsert="$3"
    
    log "INFO" "Creating seed data (type: $seed_type, count: $count, upsert: $use_upsert)..."
    
    # Create temporary seeding script
    local seed_script="${PROJECT_ROOT}/temp_seed_script.py"
    
    cat > "$seed_script" << 'EOF'
#!/usr/bin/env python3
"""
Temporary seeding script for DevPocket API
"""

import asyncio
import sys
import os
import uuid
import random
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def seed_database(seed_type: str, count: int = 10, use_upsert: bool = False):
    """Seed database with sample data using factories."""
    
    # Import required modules
    from app.db.database import AsyncSessionLocal
    from app.core.config import settings
    from app.core.logging import logger
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import insert
    
    # Import models
    from app.models.user import User
    from app.models.ssh_profile import SSHProfile, SSHKey
    from app.models.command import Command
    from app.models.session import Session
    from app.models.sync import SyncData
    
    # Import factories
    from tests.factories.user_factory import UserFactory
    from tests.factories.ssh_factory import SSHProfileFactory, SSHKeyFactory
    from tests.factories.command_factory import CommandFactory
    from tests.factories.session_factory import SessionFactory
    from tests.factories.sync_factory import SyncDataFactory
    
    logger.info(f"Starting database seeding (type: {seed_type}, count: {count}, upsert: {use_upsert})")
    
    # Add randomization seed based on timestamp for better variety
    random_seed = int(datetime.now().timestamp()) % 1000000
    random.seed(random_seed)
    logger.info(f"Using random seed: {random_seed}")
    
    try:
        # Get database session
        async with AsyncSessionLocal() as session:
            
            # Helper function for upsert operations
            async def upsert_or_add(model_class, data, unique_keys, session):
                if use_upsert:
                    stmt = insert(model_class).values(**data)
                    stmt = stmt.on_conflict_do_nothing(index_elements=unique_keys)
                    await session.execute(stmt)
                else:
                    obj = model_class(**data)
                    session.add(obj)
                    return obj
            
            created_users = []
            if seed_type in ["all", "users"]:
                logger.info(f"Creating {count} sample users...")
                
                for i in range(count):
                    # Generate unique email and username with timestamp component
                    timestamp_part = int(datetime.now().timestamp() * 1000) % 100000
                    unique_id = f"{timestamp_part}_{random.randint(1000, 9999)}"
                    
                    user_data = {
                        'id': uuid.uuid4(),
                        'email': f"user_{unique_id}@example.com",
                        'username': f"user_{unique_id}",
                        'hashed_password': '$2b$12$HYEEytPTuKa9xV058KrcO.A9CGG5EWK/L5iz6xybfYYrv8KT8kT7q',  # TestPassword123!
                        'full_name': f"Test User {unique_id}",
                        'role': random.choice(['user', 'premium']),
                        'is_active': True,
                        'is_verified': random.choice([True, False]),
                        'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 365)),
                        'updated_at': datetime.utcnow()
                    }
                    
                    if use_upsert:
                        await upsert_or_add(User, user_data, ['email'], session)
                    else:
                        user = User(**user_data)
                        session.add(user)
                        created_users.append(user)
                
                if not use_upsert:
                    await session.flush()  # Get IDs without committing
                    
                logger.info(f"Created {count} users with upsert: {use_upsert}")
            
            # Get existing users if we need them for relationships
            if seed_type != "users" and not use_upsert:
                existing_users = await session.execute(text("SELECT id FROM users ORDER BY created_at LIMIT 100"))
                user_ids = [row[0] for row in existing_users.fetchall()]
                if not user_ids and seed_type != "all":
                    logger.info("No existing users found, creating sample users first...")
                    # Create a few users for relationships
                    for i in range(min(5, count)):
                        timestamp_part = int(datetime.now().timestamp() * 1000) % 100000
                        unique_id = f"{timestamp_part}_{random.randint(1000, 9999)}"
                        user_data = {
                            'id': uuid.uuid4(),
                            'email': f"user_{unique_id}@example.com",
                            'username': f"user_{unique_id}",
                            'hashed_password': '$2b$12$HYEEytPTuKa9xV058KrcO.A9CGG5EWK/L5iz6xybfYYrv8KT8kT7q',
                            'full_name': f"Test User {unique_id}",
                            'role': 'user',
                            'is_active': True,
                            'is_verified': True,
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow()
                        }
                        user = User(**user_data)
                        session.add(user)
                        created_users.append(user)
                    await session.flush()
                    user_ids = [user.id for user in created_users]
            
            if seed_type in ["all", "ssh"]:
                logger.info(f"Creating {count} sample SSH profiles and keys...")
                
                # First create SSH keys
                ssh_keys = []
                for i in range(count):
                    if use_upsert:
                        user_id = uuid.uuid4()  # Will need to be replaced with actual user ID in production
                    else:
                        user_id = created_users[i % len(created_users)].id if created_users else user_ids[i % len(user_ids)] if user_ids else uuid.uuid4()
                    
                    key_data = {
                        'id': uuid.uuid4(),
                        'user_id': user_id,
                        'name': f"ssh-key-{random.randint(1000, 9999)}",
                        'description': f"SSH key for development {random.choice(['server', 'workstation', 'laptop'])}",
                        'key_type': random.choice(['rsa', 'ed25519', 'ecdsa']),
                        'key_size': random.choice([2048, 4096]) if random.choice([True, False]) else None,
                        'fingerprint': f"SHA256:{random.randbytes(32).hex()[:32]}",
                        'encrypted_private_key': random.randbytes(1024),
                        'public_key': f"ssh-rsa AAAAB3NzaC1yc2E{random.randbytes(32).hex()[:64]} user@example.com",
                        'comment': f"user@{random.choice(['laptop', 'desktop', 'server'])}",
                        'has_passphrase': random.choice([True, False]),
                        'file_path': f"/home/user/.ssh/id_{random.choice(['rsa', 'ed25519'])}",
                        'is_active': True,
                        'last_used_at': datetime.utcnow() - timedelta(hours=random.randint(1, 720)),
                        'usage_count': random.randint(0, 100),
                        'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 90)),
                        'updated_at': datetime.utcnow()
                    }
                    
                    if use_upsert:
                        await upsert_or_add(SSHKey, key_data, ['fingerprint'], session)
                    else:
                        ssh_key = SSHKey(**key_data)
                        session.add(ssh_key)
                        ssh_keys.append(ssh_key)
                
                if not use_upsert:
                    await session.flush()
                
                # Then create SSH profiles
                for i in range(count):
                    if use_upsert:
                        user_id = uuid.uuid4()  # Will need actual user ID
                        ssh_key_id = uuid.uuid4()  # Will need actual key ID
                    else:
                        user_id = created_users[i % len(created_users)].id if created_users else user_ids[i % len(user_ids)] if user_ids else uuid.uuid4()
                        ssh_key_id = ssh_keys[i % len(ssh_keys)].id if ssh_keys else None
                    
                    profile_data = {
                        'id': uuid.uuid4(),
                        'user_id': user_id,
                        'name': f"{random.choice(['prod', 'dev', 'staging'])}-server-{random.randint(100, 999)}",
                        'description': f"Connection to {random.choice(['production', 'development', 'staging'])} server",
                        'host': f"{random.choice(['app', 'db', 'web'])}-{random.randint(1, 10)}.example.com",
                        'port': random.choice([22, 2222, 8022]),
                        'username': random.choice(['ubuntu', 'ec2-user', 'deploy', 'admin']),
                        'auth_method': random.choice(['key', 'password']),
                        'ssh_key_id': ssh_key_id,
                        'compression': random.choice([True, False]),
                        'strict_host_key_checking': random.choice([True, False]),
                        'connection_timeout': random.randint(10, 60),
                        'ssh_options': '{"ServerAliveInterval": 60, "ServerAliveCountMax": 3}',
                        'is_active': True,
                        'last_used_at': datetime.utcnow() - timedelta(hours=random.randint(1, 168)),
                        'connection_count': random.randint(0, 50),
                        'successful_connections': 0,  # Will be calculated
                        'failed_connections': 0,      # Will be calculated
                        'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 60)),
                        'updated_at': datetime.utcnow()
                    }
                    
                    # Calculate success/failure based on connection count
                    success_rate = random.uniform(0.7, 0.98)
                    profile_data['successful_connections'] = int(profile_data['connection_count'] * success_rate)
                    profile_data['failed_connections'] = profile_data['connection_count'] - profile_data['successful_connections']
                    
                    if use_upsert:
                        await upsert_or_add(SSHProfile, profile_data, ['user_id', 'name'], session)
                    else:
                        ssh_profile = SSHProfile(**profile_data)
                        session.add(ssh_profile)
                
                if not use_upsert:
                    await session.flush()
                    
                logger.info(f"Created {count} SSH keys and profiles with upsert: {use_upsert}")
            
            # Create sessions first as they're needed for commands
            created_sessions = []
            if seed_type in ["all", "sessions", "commands"]:
                logger.info(f"Creating {count} sample sessions...")
                
                for i in range(count):
                    if use_upsert:
                        user_id = uuid.uuid4()
                    else:
                        user_id = created_users[i % len(created_users)].id if created_users else user_ids[i % len(user_ids)] if user_ids else uuid.uuid4()
                    
                    session_data = {
                        'id': uuid.uuid4(),
                        'user_id': user_id,
                        'device_id': f"device-{random.randbytes(8).hex()}",
                        'device_type': random.choice(['mobile', 'tablet', 'desktop']),
                        'device_name': f"{random.choice(['iPhone', 'Android', 'iPad', 'MacBook', 'Windows'])} {random.randint(1, 15)}",
                        'session_name': f"Session {random.randint(1, 1000)}",
                        'session_type': random.choice(['terminal', 'ssh', 'local']),
                        'user_agent': f"DevPocket/{random.uniform(1.0, 2.0):.1f}",
                        'ip_address': f"{random.randint(192, 192)}.{random.randint(168, 168)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
                        'is_active': random.choice([True, False]),
                        'last_activity_at': datetime.utcnow() - timedelta(minutes=random.randint(1, 1440)),
                        'ended_at': datetime.utcnow() - timedelta(minutes=random.randint(1, 60)) if random.choice([True, False]) else None,
                        'ssh_host': f"server-{random.randint(1, 100)}.example.com" if random.choice([True, False]) else None,
                        'ssh_port': random.choice([22, 2222]) if random.choice([True, False]) else None,
                        'ssh_username': random.choice(['ubuntu', 'deploy']) if random.choice([True, False]) else None,
                        'terminal_cols': random.choice([80, 120, 132]),
                        'terminal_rows': random.choice([24, 30, 40]),
                        'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                        'updated_at': datetime.utcnow()
                    }
                    
                    if use_upsert:
                        await upsert_or_add(Session, session_data, ['device_id'], session)
                    else:
                        session_obj = Session(**session_data)
                        session.add(session_obj)
                        created_sessions.append(session_obj)
                
                if not use_upsert:
                    await session.flush()
                    
                logger.info(f"Created {count} sessions with upsert: {use_upsert}")
            
            if seed_type in ["all", "commands"]:
                logger.info(f"Creating {count} sample commands...")
                
                # Get existing sessions if needed
                if not created_sessions and not use_upsert:
                    existing_sessions = await session.execute(text("SELECT id FROM sessions ORDER BY created_at LIMIT 100"))
                    session_ids = [row[0] for row in existing_sessions.fetchall()]
                    if not session_ids:
                        logger.warning("No sessions found for commands, skipping command creation")
                    else:
                        session_ids = session_ids
                else:
                    session_ids = [s.id for s in created_sessions] if created_sessions else []
                
                sample_commands = [
                    "ls -la", "pwd", "cd /home", "cat README.md", "ps aux", "top",
                    "docker ps", "kubectl get pods", "git status", "npm install",
                    "python manage.py migrate", "ssh user@server", "vim config.py",
                    "grep -r 'TODO' .", "find . -name '*.py'", "tail -f logs/app.log",
                    "systemctl status nginx", "df -h", "free -m", "htop"
                ]
                
                for i in range(count):
                    if use_upsert or not session_ids:
                        session_id = uuid.uuid4()
                    else:
                        session_id = session_ids[i % len(session_ids)]
                    
                    command_text = random.choice(sample_commands)
                    command_data = {
                        'id': uuid.uuid4(),
                        'session_id': session_id,
                        'command': command_text,
                        'output': f"Output for {command_text}\n" + "\n".join([f"line {j}" for j in range(random.randint(1, 10))]),
                        'error_output': "Permission denied" if random.random() < 0.1 else None,
                        'exit_code': random.choice([0, 0, 0, 0, 1, 2]) if random.random() < 0.9 else random.randint(0, 255),
                        'status': random.choice(['completed', 'completed', 'completed', 'failed']),
                        'started_at': datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                        'completed_at': datetime.utcnow() - timedelta(minutes=random.randint(0, 59)),
                        'execution_time': random.uniform(0.1, 30.0),
                        'working_directory': random.choice(['/home/user', '/app', '/var/www', '/opt/project']),
                        'environment_vars': '{"PATH": "/usr/bin:/bin", "HOME": "/home/user"}',
                        'was_ai_suggested': random.choice([True, False]),
                        'ai_explanation': f"This command {command_text} is used for..." if random.choice([True, False]) else None,
                        'command_type': random.choice(['system', 'git', 'docker', 'file', 'network']),
                        'is_sensitive': random.choice([True, False]),
                        'created_at': datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                        'updated_at': datetime.utcnow()
                    }
                    
                    if use_upsert:
                        await upsert_or_add(Command, command_data, ['session_id', 'command'], session)
                    else:
                        command_obj = Command(**command_data)
                        session.add(command_obj)
                
                if not use_upsert:
                    await session.flush()
                    
                logger.info(f"Created {count} commands with upsert: {use_upsert}")
            
            if seed_type in ["all", "sync"]:
                logger.info(f"Creating {count} sample sync data...")
                
                sync_types = ['commands', 'ssh_profiles', 'settings', 'workflows', 'preferences']
                device_types = ['mobile', 'tablet', 'desktop', 'laptop']
                
                for i in range(count):
                    if use_upsert:
                        user_id = uuid.uuid4()
                    else:
                        user_id = created_users[i % len(created_users)].id if created_users else user_ids[i % len(user_ids)] if user_ids else uuid.uuid4()
                    
                    sync_data_obj = {
                        'id': uuid.uuid4(),
                        'user_id': user_id,
                        'sync_type': random.choice(sync_types),
                        'sync_key': f"key-{random.randint(1000, 9999)}-{random.randbytes(4).hex()}",
                        'data': {
                            'content': f"Sample sync data {i}",
                            'version': random.randint(1, 10),
                            'metadata': {'source': 'seeding', 'created': datetime.utcnow().isoformat()}
                        },
                        'version': random.randint(1, 5),
                        'is_deleted': False,
                        'source_device_id': f"device-{random.randbytes(8).hex()}",
                        'source_device_type': random.choice(device_types),
                        'conflict_data': {'conflicts': []} if random.random() < 0.1 else None,
                        'resolved_at': datetime.utcnow() if random.random() < 0.05 else None,
                        'synced_at': datetime.utcnow() - timedelta(minutes=random.randint(1, 1440)),
                        'last_modified_at': datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                        'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                        'updated_at': datetime.utcnow()
                    }
                    
                    if use_upsert:
                        await upsert_or_add(SyncData, sync_data_obj, ['user_id', 'sync_key'], session)
                    else:
                        sync_obj = SyncData(**sync_data_obj)
                        session.add(sync_obj)
                
                if not use_upsert:
                    await session.flush()
                    
                logger.info(f"Created {count} sync data records with upsert: {use_upsert}")
            
            # Commit all changes
            await session.commit()
            logger.info("Database seeding completed successfully")
            
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise

async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python temp_seed_script.py <seed_type> <count> [use_upsert]")
        sys.exit(1)
    
    seed_type = sys.argv[1]
    count = int(sys.argv[2])
    use_upsert = len(sys.argv) > 3 and sys.argv[3].lower() == 'true'
    
    await seed_database(seed_type, count, use_upsert)

if __name__ == "__main__":
    asyncio.run(main())
EOF
    
    # Run the seeding script
    cd "$PROJECT_ROOT"
    
    if python "$seed_script" "$seed_type" "$count" "$use_upsert"; then
        log "SUCCESS" "Database seeding completed successfully"
    else
        log "ERROR" "Database seeding failed"
        rm -f "$seed_script"
        exit 1
    fi
    
    # Clean up temporary script
    rm -f "$seed_script"
}

# Show database statistics
show_stats() {
    log "INFO" "Fetching database statistics..."
    
    # Create temporary stats script
    local stats_script="${PROJECT_ROOT}/temp_stats_script.py"
    
    cat > "$stats_script" << 'EOF'
#!/usr/bin/env python3
"""
Database statistics script
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def show_database_stats():
    """Show database table statistics."""
    from app.db.database import AsyncSessionLocal
    from app.core.logging import logger
    
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            # Query table statistics
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    relname as table_name,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables 
                ORDER BY relname;
            """))
            
            stats = result.fetchall()
            
            if stats:
                print("\nDatabase Table Statistics:")
                print("-" * 80)
                print(f"{'Table':<20} {'Live Rows':<12} {'Inserts':<10} {'Updates':<10} {'Deletes':<10}")
                print("-" * 80)
                
                for stat in stats:
                    print(f"{stat.table_name:<20} {stat.live_rows:<12} {stat.inserts:<10} {stat.updates:<10} {stat.deletes:<10}")
                
                print("-" * 80)
                print(f"Total tables: {len(stats)}")
            else:
                print("No table statistics available")
                
    except Exception as e:
        logger.error(f"Failed to fetch database statistics: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(show_database_stats())
EOF
    
    cd "$PROJECT_ROOT"
    
    if python "$stats_script"; then
        log "SUCCESS" "Database statistics retrieved"
    else
        log "WARN" "Failed to retrieve database statistics"
    fi
    
    # Clean up temporary script
    rm -f "$stats_script"
}

# Show help message
show_help() {
    cat << EOF
DevPocket API - Database Seeding Script

USAGE:
    $0 [OPTIONS] [SEED_TYPE] [COUNT]

OPTIONS:
    -h, --help          Show this help message
    --clean             Clean existing data before seeding (prompts for confirmation)
    --clean-force       Force clean existing data without confirmation
    --reset             Reset entire database (drop all data and recreate schema)
    --reset-force       Force reset without confirmation
    --upsert            Use upsert operations to handle conflicts (ON CONFLICT DO NOTHING)
    --stats             Show database statistics after seeding
    --stats-only        Only show database statistics, don't seed
    --env-file FILE     Specify environment file to use (default: .env)

ARGUMENTS:
    SEED_TYPE           Type of data to seed (default: all)
                       Options: all, users, ssh, commands, sessions, sync
    COUNT              Number of records to create per type (default: 10)

SEED TYPES:
    all                Create sample data for all entity types
    users              Create sample users only
    ssh                Create sample SSH connections (with users)
    commands           Create sample commands (with users) 
    sessions           Create sample sessions (with users)
    sync               Create sample sync data (with users)

EXAMPLES:
    $0                          # Seed all types with 10 records each
    $0 users 25                 # Create 25 sample users
    $0 ssh 15                   # Create 15 SSH connections (with users)
    $0 all 5                    # Create 5 records of each type
    $0 --clean users 10         # Clean users then seed 10 new ones
    $0 --clean-force all 20     # Force clean all data then seed 20 of each
    $0 --reset --upsert all 50  # Reset database then seed 50 with upserts
    $0 --stats-only             # Show database statistics only
    $0 commands 20 --stats      # Create 20 commands and show stats

PREREQUISITES:
    - Database must be running and accessible
    - Database migrations must be up to date (run db_migrate.sh first)
    - Test factories must be available in tests/factories/

ENVIRONMENT:
    Uses same database connection settings as main application.
    Set DATABASE_URL or individual variables in .env file.

EOF
}

# Main function
main() {
    local seed_type="all"
    local count=10
    local show_stats_flag=false
    local stats_only=false
    local clean_data_flag=false
    local clean_force=false
    local reset_db_flag=false
    local reset_force=false
    local use_upsert=false
    local env_file=".env"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --clean)
                clean_data_flag=true
                ;;
            --clean-force)
                clean_data_flag=true
                clean_force=true
                ;;
            --reset)
                reset_db_flag=true
                ;;
            --reset-force)
                reset_db_flag=true
                reset_force=true
                ;;
            --upsert)
                use_upsert=true
                ;;
            --stats)
                show_stats_flag=true
                ;;
            --stats-only)
                stats_only=true
                ;;
            --env-file)
                if [[ -n "${2:-}" ]]; then
                    env_file="$2"
                    shift
                else
                    log "ERROR" "Environment file path required with --env-file option"
                    exit 1
                fi
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ "$1" =~ ^[0-9]+$ ]]; then
                    count="$1"
                else
                    seed_type="$1"
                fi
                ;;
        esac
        shift
    done
    
    # Validate seed type
    case "$seed_type" in
        all|users|ssh|commands|sessions|sync)
            # Valid seed type
            ;;
        *)
            log "ERROR" "Invalid seed type: $seed_type"
            log "INFO" "Valid types: all, users, ssh, commands, sessions, sync"
            exit 1
            ;;
    esac
    
    log "INFO" "Starting database seeding script..."
    log "INFO" "Project root: $PROJECT_ROOT"
    log "INFO" "Seed type: $seed_type"
    log "INFO" "Count: $count"
    log "INFO" "Use upsert: $use_upsert"
    log "INFO" "Clean data: $clean_data_flag"
    log "INFO" "Reset database: $reset_db_flag"
    log "INFO" "Environment file: $env_file"
    
    # Set environment file for Python scripts
    export ENV_FILE="$env_file"
    
    # Activate virtual environment
    activate_venv
    
    # Check database connection
    check_database
    
    # Handle stats-only mode
    if [[ "$stats_only" == true ]]; then
        show_stats
        exit 0
    fi
    
    # Handle database reset
    if [[ "$reset_db_flag" == true ]]; then
        reset_database "$reset_force"
    fi
    
    # Handle data cleaning
    if [[ "$clean_data_flag" == true ]]; then
        clean_data "$seed_type" "$clean_force"
    fi
    
    # Run seeding
    run_seeding "$seed_type" "$count" "$use_upsert"
    
    # Show stats if requested
    if [[ "$show_stats_flag" == true ]]; then
        show_stats
    fi
    
    log "SUCCESS" "Database seeding script completed successfully"
}

# Error trap
trap 'log "ERROR" "Script failed on line $LINENO"' ERR

# Run main function
main "$@"