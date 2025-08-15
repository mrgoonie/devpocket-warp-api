# DevPocket Server Implementation
# File: main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
import jwt
import httpx
from redis import asyncio as aioredis
import asyncpg
from contextlib import asynccontextmanager

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    DATABASE_URL = "postgresql://user:password@localhost/devpocket"
    REDIS_URL = "redis://localhost:6379"
    JWT_SECRET = "your-secret-key-change-in-production"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION = 86400  # 24 hours
    # No OpenRouter API key - users bring their own (BYOK)
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
config = Config()

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    username: str
    subscription_tier: str = "free"
    created_at: datetime = Field(default_factory=datetime.now)
    
class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    device_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
class Command(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    command: str
    output: Optional[str] = None
    status: str = "pending"  # pending, running, success, error
    created_at: datetime = Field(default_factory=datetime.now)
    
class AIRequest(BaseModel):
    prompt: str
    context: Optional[List[Dict[str, str]]] = None
    model: str = "claude-3-haiku-20240307"
    
class AIResponse(BaseModel):
    suggestion: str
    explanation: Optional[str] = None
    confidence: float

# ============================================================================
# APPLICATION LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = await asyncpg.create_pool(config.DATABASE_URL)
    app.state.redis = await aioredis.from_url(config.REDIS_URL, decode_responses=True)
    logger.info("Database and Redis connections established")
    
    yield
    
    # Shutdown
    await app.state.db.close()
    await app.state.redis.close()
    logger.info("Database and Redis connections closed")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="DevPocket API",
    description="AI-Powered Mobile Terminal Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AUTHENTICATION
# ============================================================================

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(seconds=config.JWT_EXPIRATION)
    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[session_id] = user_id
        logger.info(f"WebSocket connected: session={session_id}, user={user_id}")
        
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            del self.user_sessions[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")
            
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
            
    async def broadcast_to_user(self, user_id: str, message: dict):
        sessions = [s for s, u in self.user_sessions.items() if u == user_id]
        for session_id in sessions:
            await self.send_message(session_id, message)

manager = ConnectionManager()

# ============================================================================
# SSH/PTY EXECUTOR
# ============================================================================

import paramiko
import pty
import os
import select
import termios
import struct
import fcntl

class SSHExecutor:
    def __init__(self):
        self.sessions: Dict[str, paramiko.SSHClient] = {}
        self.channels: Dict[str, paramiko.Channel] = {}
        
    async def connect_ssh(self, session_id: str, host: str, port: int, 
                          username: str, password: str = None, key_path: str = None):
        """Connect to SSH server"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if key_path:
                client.connect(host, port, username, key_filename=key_path)
            else:
                client.connect(host, port, username, password=password)
                
            self.sessions[session_id] = client
            
            # Create PTY channel
            channel = client.invoke_shell(term='xterm-256color')
            channel.settimeout(0.0)
            self.channels[session_id] = channel
            
            return True
        except Exception as e:
            logger.error(f"SSH connection error: {e}")
            return False
            
    def create_pty_session(self, session_id: str):
        """Create local PTY session"""
        master, slave = pty.openpty()
        self.sessions[session_id] = {
            'master': master,
            'slave': slave,
            'pid': None
        }
        return master
        
    async def execute_command_ssh(self, session_id: str, command: str):
        """Execute command via SSH"""
        if session_id not in self.channels:
            raise Exception("No SSH session")
            
        channel = self.channels[session_id]
        channel.send(command + '\n')
        
        # Read output
        output = ""
        while channel.recv_ready():
            output += channel.recv(1024).decode('utf-8')
            await asyncio.sleep(0.01)
            
        return output
        
    async def send_pty_input(self, session_id: str, input_data: str):
        """Send input to PTY"""
        if session_id in self.channels:
            # SSH PTY
            self.channels[session_id].send(input_data)
        elif session_id in self.sessions:
            # Local PTY
            os.write(self.sessions[session_id]['master'], input_data.encode())
            
    async def read_pty_output(self, session_id: str) -> AsyncGenerator:
        """Read PTY output stream"""
        if session_id in self.channels:
            # SSH PTY
            channel = self.channels[session_id]
            while True:
                if channel.recv_ready():
                    data = channel.recv(1024).decode('utf-8', errors='ignore')
                    yield {"type": "pty_output", "data": data}
                else:
                    await asyncio.sleep(0.01)
        elif session_id in self.sessions:
            # Local PTY
            master = self.sessions[session_id]['master']
            while True:
                r, w, e = select.select([master], [], [], 0)
                if master in r:
                    data = os.read(master, 1024).decode('utf-8', errors='ignore')
                    yield {"type": "pty_output", "data": data}
                else:
                    await asyncio.sleep(0.01)
                    
    def resize_pty(self, session_id: str, cols: int, rows: int):
        """Resize PTY window"""
        if session_id in self.channels:
            # SSH PTY
            self.channels[session_id].resize_pty(width=cols, height=rows)
        elif session_id in self.sessions:
            # Local PTY
            master = self.sessions[session_id]['master']
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
            
    def disconnect(self, session_id: str):
        """Disconnect session"""
        if session_id in self.sessions:
            if isinstance(self.sessions[session_id], dict):
                # Local PTY
                os.close(self.sessions[session_id]['master'])
                os.close(self.sessions[session_id]['slave'])
            else:
                # SSH
                self.sessions[session_id].close()
            del self.sessions[session_id]
            
        if session_id in self.channels:
            self.channels[session_id].close()
            del self.channels[session_id]

ssh_executor = SSHExecutor()

# ============================================================================
# TERMINAL EXECUTOR (keeping for backwards compatibility)
# ============================================================================

class TerminalExecutor:
    def __init__(self):
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        
    async def execute_command(self, session_id: str, command: str) -> AsyncGenerator:
        """Execute command and stream output"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )
            
            self.processes[session_id] = process
            
            # Stream output
            while True:
                stdout = await process.stdout.read(1024)
                stderr = await process.stderr.read(1024)
                
                if stdout:
                    yield {"type": "stdout", "data": stdout.decode()}
                if stderr:
                    yield {"type": "stderr", "data": stderr.decode()}
                    
                if process.returncode is not None:
                    break
                    
            # Get exit code
            await process.wait()
            yield {"type": "exit", "code": process.returncode}
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            yield {"type": "error", "message": str(e)}
        finally:
            if session_id in self.processes:
                del self.processes[session_id]
                
    async def kill_process(self, session_id: str):
        if session_id in self.processes:
            self.processes[session_id].kill()
            await self.processes[session_id].wait()

terminal = TerminalExecutor()

# ============================================================================
# AI SERVICE
# ============================================================================

class AIService:
    def __init__(self):
        self.base_url = config.OPENROUTER_BASE_URL
        
    async def get_command_suggestion(self, prompt: str, api_key: str, context: List[Dict] = None) -> str:
        """Get AI command suggestion from natural language using user's API key"""
        
        # Create client with user's API key
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://devpocket.app",
                "X-Title": "DevPocket"
            }
        ) as client:
            messages = []
            if context:
                messages.extend(context)
                
            messages.append({
                "role": "system",
                "content": "You are a terminal command assistant. Convert natural language requests to shell commands. Return only the command, no explanation."
            })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": "google/gemini-2.5-flash",
                        "messages": messages,
                        "max_tokens": 150,
                        "temperature": 0.3
                    }
                )
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except Exception as e:
                logger.error(f"AI service error: {e}")
                return None
            
    async def explain_error(self, command: str, error: str, api_key: str) -> str:
        """Explain command error with AI using user's API key"""
        
        prompt = f"""
        Command: {command}
        Error: {error}
        
        Explain this error and suggest how to fix it. Be concise.
        """
        
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://devpocket.app",
                "X-Title": "DevPocket"
            }
        ) as client:
            try:
                response = await client.post(
                    "/chat/completions",
                    json={
                        "model": "google/gemini-2.5-flash",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 300,
                        "temperature": 0.5
                    }
                )
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
            except Exception as e:
                logger.error(f"AI explain error: {e}")
                return "Unable to explain error at this time."
                
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenRouter API key"""
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
            }
        ) as client:
            try:
                response = await client.get("/models")
                return response.status_code == 200
            except:
                return False

ai_service = AIService()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "name": "DevPocket API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.post("/api/auth/register")
async def register(email: str, username: str, password: str):
    """Register new user"""
    
    # Check if user exists
    async with app.state.db.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1 OR username = $2",
            email, username
        )
        
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
            
        # Create user
        user_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO users (id, email, username, password_hash, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id, email, username, hash_password(password), datetime.now()
        )
        
    # Generate token
    token = create_access_token(user_id)
    
    return {
        "user_id": user_id,
        "token": token,
        "token_type": "bearer"
    }

@app.post("/api/auth/login")
async def login(username: str, password: str):
    """Login user"""
    
    async with app.state.db.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, password_hash FROM users WHERE username = $1 OR email = $1",
            username
        )
        
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    token = create_access_token(user["id"])
    
    return {
        "user_id": user["id"],
        "token": token,
        "token_type": "bearer"
    }

@app.get("/api/sessions")
async def get_sessions(user_id: str = Depends(get_current_user)):
    """Get user sessions"""
    
    async with app.state.db.acquire() as conn:
        sessions = await conn.fetch(
            "SELECT * FROM sessions WHERE user_id = $1 ORDER BY created_at DESC",
            user_id
        )
        
    return [dict(s) for s in sessions]

@app.get("/api/commands/history")
async def get_command_history(
    limit: int = 100,
    user_id: str = Depends(get_current_user)
):
    """Get command history"""
    
    async with app.state.db.acquire() as conn:
        commands = await conn.fetch(
            """
            SELECT c.* FROM commands c
            JOIN sessions s ON c.session_id = s.id
            WHERE s.user_id = $1
            ORDER BY c.created_at DESC
            LIMIT $2
            """,
            user_id, limit
        )
        
    return [dict(c) for c in commands]

@app.post("/api/ai/suggest")
async def get_ai_suggestion(
    request: AIRequest,
    api_key: str,  # User's OpenRouter API key
    user_id: str = Depends(get_current_user)
):
    """Get AI command suggestion using user's API key (BYOK)"""
    
    # Validate API key
    if not await ai_service.validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid OpenRouter API key")
    
    # Check cache first
    cache_key = f"ai_cache:{request.prompt}"
    cached = await app.state.redis.get(cache_key)
    if cached:
        return {"suggestion": cached, "cached": True}
    
    # Get suggestion using user's API key
    suggestion = await ai_service.get_command_suggestion(
        request.prompt,
        api_key,
        request.context
    )
    
    if not suggestion:
        raise HTTPException(status_code=500, detail="Failed to generate suggestion")
    
    # Cache result
    await app.state.redis.setex(cache_key, 3600, suggestion)
    
    # Log usage for analytics (not billing since BYOK)
    await app.state.redis.hincrby(
        f"ai_usage:{user_id}:{datetime.now().strftime('%Y-%m-%d')}",
        "requests",
        1
    )
    
    return {"suggestion": suggestion, "cached": False}

@app.post("/api/ai/explain")
async def explain_error(
    command: str,
    error: str,
    api_key: str,  # User's OpenRouter API key
    user_id: str = Depends(get_current_user)
):
    """Explain command error using user's API key (BYOK)"""
    
    # Validate API key
    if not await ai_service.validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid OpenRouter API key")
    
    explanation = await ai_service.explain_error(command, error, api_key)
    
    return {"explanation": explanation}

@app.post("/api/ai/validate-key")
async def validate_api_key(
    api_key: str,
    user_id: str = Depends(get_current_user)
):
    """Validate OpenRouter API key"""
    
    is_valid = await ai_service.validate_api_key(api_key)
    
    if is_valid:
        # Optionally store encrypted key reference (not the key itself)
        async with app.state.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET has_api_key = true, api_key_validated_at = $1
                WHERE id = $2
                """,
                datetime.now(), user_id
            )
    
    return {"valid": is_valid}

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket, token: str):
    """WebSocket terminal connection with SSH/PTY support"""
    
    # Verify token
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except:
        await websocket.close(code=4001, reason="Invalid token")
        return
        
    # Create session
    session_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id, user_id)
    
    # Store session in database
    async with app.state.db.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sessions (id, user_id, device_id, created_at)
            VALUES ($1, $2, $3, $4)
            """,
            session_id, user_id, "mobile", datetime.now()
        )
    
    # PTY reader task
    pty_reader_task = None
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "command":
                # Execute single command via SSH
                command = data.get("data")
                
                # Store command
                command_id = str(uuid.uuid4())
                async with app.state.db.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO commands (id, session_id, command, status, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        command_id, session_id, command, "running", datetime.now()
                    )
                
                # Execute via SSH if connected, otherwise local
                if session_id in ssh_executor.sessions:
                    output = await ssh_executor.execute_command_ssh(session_id, command)
                    await manager.send_message(session_id, {
                        "type": "command_output",
                        "command_id": command_id,
                        "data": output
                    })
                else:
                    # Execute locally
                    async for output in terminal.execute_command(session_id, command):
                        await manager.send_message(session_id, {
                            "type": "output",
                            "command_id": command_id,
                            "data": output
                        })
                        
            elif message_type == "connect_ssh":
                # Connect to SSH server
                ssh_config = data.get("config")
                success = await ssh_executor.connect_ssh(
                    session_id,
                    ssh_config["host"],
                    ssh_config.get("port", 22),
                    ssh_config["username"],
                    ssh_config.get("password"),
                    ssh_config.get("key_path")
                )
                
                if success:
                    # Start PTY output reader
                    pty_reader_task = asyncio.create_task(
                        _read_pty_output(session_id, manager)
                    )
                    
                await manager.send_message(session_id, {
                    "type": "ssh_connected" if success else "ssh_error",
                    "session_id": session_id
                })
                    
            elif message_type == "create_pty":
                # Create local PTY session
                master = ssh_executor.create_pty_session(session_id)
                
                # Start PTY output reader
                pty_reader_task = asyncio.create_task(
                    _read_pty_output(session_id, manager)
                )
                
                await manager.send_message(session_id, {
                    "type": "pty_created",
                    "session_id": session_id
                })
                
            elif message_type == "pty_input":
                # Send input to PTY
                input_data = data.get("data")
                await ssh_executor.send_pty_input(session_id, input_data)
                
            elif message_type == "resize_pty":
                # Resize PTY window
                cols = data.get("cols", 80)
                rows = data.get("rows", 24)
                ssh_executor.resize_pty(session_id, cols, rows)
                
            elif message_type == "ai_convert":
                # Convert natural language to command (BYOK)
                prompt = data.get("prompt")
                api_key = data.get("api_key")
                
                if not api_key:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "OpenRouter API key required"
                    })
                    continue
                    
                command = await ai_service.get_command_suggestion(prompt, api_key)
                
                await manager.send_message(session_id, {
                    "type": "ai_suggestion",
                    "command": command
                })
                
            elif message_type == "kill":
                await terminal.kill_process(session_id)
                
            elif message_type == "sync":
                # Sync commands across devices
                await sync_user_commands(user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        ssh_executor.disconnect(session_id)
        if pty_reader_task:
            pty_reader_task.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(session_id)
        ssh_executor.disconnect(session_id)
        if pty_reader_task:
            pty_reader_task.cancel()

async def _read_pty_output(session_id: str, manager: ConnectionManager):
    """Background task to read PTY output"""
    try:
        async for output in ssh_executor.read_pty_output(session_id):
            await manager.send_message(session_id, output)
    except Exception as e:
        logger.error(f"PTY reader error: {e}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    import bcrypt
    return bcrypt.checkpw(password.encode(), hashed.encode())

async def get_user_subscription(user_id: str) -> str:
    """Get user subscription tier"""
    async with app.state.db.acquire() as conn:
        result = await conn.fetchval(
            "SELECT subscription_tier FROM users WHERE id = $1",
            user_id
        )
    return result or "free"

async def sync_user_commands(user_id: str):
    """Sync commands across user devices"""
    async with app.state.db.acquire() as conn:
        recent_commands = await conn.fetch(
            """
            SELECT c.* FROM commands c
            JOIN sessions s ON c.session_id = s.id
            WHERE s.user_id = $1
            ORDER BY c.created_at DESC
            LIMIT 50
            """,
            user_id
        )
        
    # Broadcast to all user sessions
    await manager.broadcast_to_user(user_id, {
        "type": "sync",
        "commands": [dict(c) for c in recent_commands]
    })

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )