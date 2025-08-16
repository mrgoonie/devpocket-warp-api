# DevPocket API Developer Integration Guide

## Overview

This comprehensive guide helps developers integrate with the DevPocket API, covering everything from basic setup to advanced features like real-time terminal communication and AI-powered command assistance.

## Table of Contents

1. [Quick Start](#quick-start)
2. [SDK Installation](#sdk-installation)
3. [Authentication Setup](#authentication-setup)
4. [Core Features](#core-features)
5. [Advanced Integration](#advanced-integration)
6. [Platform-Specific Examples](#platform-specific-examples)
7. [Testing and Debugging](#testing-and-debugging)
8. [Production Deployment](#production-deployment)

## Quick Start

### 1. Get API Access

1. **Register for DevPocket account** at [devpocket.app](https://devpocket.app)
2. **Obtain API credentials** from your dashboard
3. **Get OpenRouter API key** from [openrouter.ai](https://openrouter.ai) for AI features

### 2. Basic API Call

```bash
# Test API connectivity
curl -X GET "https://api.devpocket.app/health" \
  -H "Accept: application/json"
```

```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### 3. Authenticate and Create Session

```bash
# Register new user
curl -X POST "https://api.devpocket.app/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "username": "devuser",
    "password": "SecurePass123!",
    "display_name": "Developer User"
  }'

# Response includes access token
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { ... }
}
```

## SDK Installation

### JavaScript/TypeScript

```bash
npm install @devpocket/api-client
# or
yarn add @devpocket/api-client
```

```typescript
import { DevPocketClient } from '@devpocket/api-client';

const client = new DevPocketClient({
  apiUrl: 'https://api.devpocket.app',
  apiKey: 'your-api-key', // Optional: for server-side usage
});
```

### Python

```bash
pip install devpocket-python
```

```python
from devpocket import DevPocketClient

client = DevPocketClient(
    api_url='https://api.devpocket.app',
    api_key='your-api-key'  # Optional: for server-side usage
)
```

### Flutter/Dart

```yaml
# pubspec.yaml
dependencies:
  devpocket_api: ^1.0.0
```

```dart
import 'package:devpocket_api/devpocket_api.dart';

final client = DevPocketClient(
  apiUrl: 'https://api.devpocket.app',
);
```

### Go

```bash
go get github.com/devpocket/go-client
```

```go
import "github.com/devpocket/go-client/devpocket"

client := devpocket.NewClient(&devpocket.Config{
    APIURL: "https://api.devpocket.app",
    APIKey: "your-api-key", // Optional
})
```

## Authentication Setup

### Client-Side Authentication (Web/Mobile)

```typescript
class DevPocketAuth {
  private client: DevPocketClient;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = new DevPocketClient({
      apiUrl: process.env.REACT_APP_API_URL || 'https://api.devpocket.app'
    });
  }

  async login(username: string, password: string): Promise<User> {
    const response = await this.client.auth.login({
      username,
      password
    });

    this.accessToken = response.access_token;
    this.refreshToken = response.refresh_token;
    
    // Store tokens securely
    this.storeTokensSecurely(response.access_token, response.refresh_token);
    
    return response.user;
  }

  async register(userData: RegisterRequest): Promise<User> {
    const response = await this.client.auth.register(userData);
    
    this.accessToken = response.access_token;
    this.refreshToken = response.refresh_token;
    
    this.storeTokensSecurely(response.access_token, response.refresh_token);
    
    return response.user;
  }

  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) return false;

    try {
      const response = await this.client.auth.refresh({
        refresh_token: this.refreshToken
      });
      
      this.accessToken = response.access_token;
      this.storeTokenSecurely('access_token', response.access_token);
      
      return true;
    } catch (error) {
      this.logout();
      return false;
    }
  }

  async logout(): Promise<void> {
    if (this.accessToken) {
      try {
        await this.client.auth.logout();
      } catch (error) {
        console.warn('Logout request failed:', error);
      }
    }
    
    this.clearTokens();
  }

  getAuthenticatedClient(): DevPocketClient {
    return new DevPocketClient({
      apiUrl: this.client.apiUrl,
      accessToken: this.accessToken,
      onTokenRefresh: () => this.refreshAccessToken()
    });
  }

  private storeTokensSecurely(accessToken: string, refreshToken: string): void {
    // Implementation depends on platform
    // Web: Store in httpOnly cookies or secure session storage
    // Mobile: Store in encrypted keychain/keystore
    
    if (typeof window !== 'undefined') {
      // Browser environment
      sessionStorage.setItem('devpocket_access_token', accessToken);
      localStorage.setItem('devpocket_refresh_token', refreshToken);
    }
  }

  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('devpocket_access_token');
      localStorage.removeItem('devpocket_refresh_token');
    }
  }
}
```

### Server-Side Authentication (API Keys)

```typescript
// For server-to-server communication
class DevPocketServerClient {
  private client: DevPocketClient;

  constructor(apiKey: string) {
    this.client = new DevPocketClient({
      apiUrl: 'https://api.devpocket.app',
      apiKey: apiKey
    });
  }

  async createUserSession(userId: string, sessionConfig: any): Promise<Session> {
    return this.client.sessions.create({
      user_id: userId,
      ...sessionConfig
    });
  }

  async getUserSessions(userId: string): Promise<Session[]> {
    return this.client.sessions.list({ user_id: userId });
  }
}
```

## Core Features

### 1. SSH Profile Management

```typescript
class SSHProfileManager {
  constructor(private client: DevPocketClient) {}

  async createProfile(profileData: CreateSSHProfileRequest): Promise<SSHProfile> {
    return this.client.ssh.profiles.create({
      name: profileData.name,
      hostname: profileData.hostname,
      username: profileData.username,
      port: profileData.port || 22,
      auth_method: profileData.auth_method,
      // Credentials are encrypted before transmission
      ...(profileData.auth_method === 'password' && {
        password: profileData.password
      }),
      ...(profileData.auth_method === 'key' && {
        ssh_key_id: profileData.ssh_key_id
      })
    });
  }

  async listProfiles(): Promise<SSHProfile[]> {
    const response = await this.client.ssh.profiles.list();
    return response.profiles;
  }

  async testConnection(profileId: string): Promise<ConnectionTestResult> {
    return this.client.ssh.profiles.test(profileId);
  }

  async deleteProfile(profileId: string): Promise<void> {
    await this.client.ssh.profiles.delete(profileId);
  }
}

// Usage example
const sshManager = new SSHProfileManager(authenticatedClient);

// Create SSH profile
const profile = await sshManager.createProfile({
  name: 'Production Server',
  hostname: 'prod.example.com',
  username: 'deploy',
  port: 22,
  auth_method: 'key',
  ssh_key_id: 'key-uuid'
});

// Test connection
const testResult = await sshManager.testConnection(profile.id);
if (testResult.success) {
  console.log('✅ SSH connection successful');
} else {
  console.error('❌ SSH connection failed:', testResult.error);
}
```

### 2. Terminal Session Management

```typescript
class TerminalSessionManager {
  constructor(private client: DevPocketClient) {}

  async createSession(config: CreateSessionRequest): Promise<Session> {
    return this.client.sessions.create({
      name: config.name,
      session_type: config.session_type, // 'ssh', 'local', 'docker'
      ...(config.session_type === 'ssh' && {
        ssh_profile_id: config.ssh_profile_id
      }),
      auto_connect: config.auto_connect || false
    });
  }

  async listSessions(): Promise<Session[]> {
    const response = await this.client.sessions.list();
    return response.sessions;
  }

  async getSession(sessionId: string): Promise<Session> {
    return this.client.sessions.get(sessionId);
  }

  async updateSession(sessionId: string, updates: Partial<Session>): Promise<Session> {
    return this.client.sessions.update(sessionId, updates);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.sessions.delete(sessionId);
  }
}

// Usage example
const sessionManager = new TerminalSessionManager(authenticatedClient);

// Create SSH session
const session = await sessionManager.createSession({
  name: 'Production Debugging',
  session_type: 'ssh',
  ssh_profile_id: profile.id,
  auto_connect: true
});

console.log('Session created:', session.id);
```

### 3. WebSocket Terminal Communication

```typescript
class TerminalWebSocket {
  private websocket: WebSocket;
  private sessionId: string | null = null;
  
  constructor(
    private apiUrl: string,
    private accessToken: string,
    private deviceId?: string
  ) {}

  async connect(): Promise<void> {
    const wsUrl = this.buildWebSocketUrl();
    
    return new Promise((resolve, reject) => {
      this.websocket = new WebSocket(wsUrl);
      
      this.websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        this.setupMessageHandlers();
        resolve();
      };
      
      this.websocket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        reject(error);
      };
      
      this.websocket.onclose = (event) => {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        this.handleReconnection();
      };
    });
  }

  async createSSHSession(
    sshProfileId: string, 
    terminalSize: { rows: number; cols: number }
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const connectMessage = {
        type: 'connect',
        data: {
          session_type: 'ssh',
          ssh_profile_id: sshProfileId,
          terminal_size: terminalSize
        }
      };

      // Set up one-time listener for session info
      const handleSessionInfo = (message: any) => {
        if (message.type === 'session_info') {
          this.sessionId = message.session_id;
          resolve(message.session_id);
        } else if (message.type === 'error') {
          reject(new Error(message.data.message));
        }
      };

      this.addMessageListener(handleSessionInfo);
      this.sendMessage(connectMessage);
    });
  }

  sendInput(input: string): void {
    if (!this.sessionId) {
      throw new Error('No active session');
    }

    this.sendMessage({
      type: 'input',
      session_id: this.sessionId,
      data: input,
      timestamp: new Date().toISOString()
    });
  }

  resizeTerminal(rows: number, cols: number): void {
    if (!this.sessionId) return;

    this.sendMessage({
      type: 'resize',
      session_id: this.sessionId,
      data: { rows, cols }
    });
  }

  sendSignal(signal: string): void {
    if (!this.sessionId) return;

    this.sendMessage({
      type: 'signal',
      session_id: this.sessionId,
      data: { signal }
    });
  }

  onOutput(callback: (output: string) => void): void {
    this.addMessageListener((message) => {
      if (message.type === 'output' && message.session_id === this.sessionId) {
        callback(message.data);
      }
    });
  }

  onStatus(callback: (status: any) => void): void {
    this.addMessageListener((message) => {
      if (message.type === 'status' && message.session_id === this.sessionId) {
        callback(message.data);
      }
    });
  }

  onError(callback: (error: any) => void): void {
    this.addMessageListener((message) => {
      if (message.type === 'error') {
        callback(message.data);
      }
    });
  }

  private buildWebSocketUrl(): string {
    const protocol = this.apiUrl.startsWith('https') ? 'wss' : 'ws';
    const baseUrl = this.apiUrl.replace(/^https?/, protocol);
    const params = new URLSearchParams({
      token: this.accessToken,
      ...(this.deviceId && { device_id: this.deviceId })
    });
    
    return `${baseUrl}/ws/terminal?${params}`;
  }

  private sendMessage(message: any): void {
    if (this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, message queued');
      // Implement message queuing if needed
    }
  }

  private setupMessageHandlers(): void {
    this.websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.messageListeners.forEach(listener => listener(message));
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
  }

  private messageListeners: Array<(message: any) => void> = [];

  private addMessageListener(listener: (message: any) => void): void {
    this.messageListeners.push(listener);
  }

  private handleReconnection(): void {
    // Implement exponential backoff reconnection
    setTimeout(() => {
      console.log('🔄 Attempting to reconnect...');
      this.connect().catch(console.error);
    }, 1000);
  }

  disconnect(): void {
    if (this.websocket) {
      this.websocket.close();
    }
  }
}

// Usage example
const terminal = new TerminalWebSocket(
  'wss://api.devpocket.app',
  accessToken,
  'device-123'
);

await terminal.connect();

// Set up event handlers
terminal.onOutput((output) => {
  document.getElementById('terminal-output').textContent += output;
});

terminal.onStatus((status) => {
  console.log('Terminal status:', status);
});

terminal.onError((error) => {
  console.error('Terminal error:', error);
});

// Create SSH session
const sessionId = await terminal.createSSHSession(profileId, { rows: 24, cols: 80 });

// Send commands
terminal.sendInput('ls -la\n');
terminal.sendInput('pwd\n');
```

### 4. AI Command Assistance (BYOK)

```typescript
class AICommandAssistant {
  constructor(
    private client: DevPocketClient,
    private openRouterApiKey: string
  ) {}

  async validateApiKey(): Promise<APIKeyValidationResponse> {
    return this.client.ai.validateKey({
      api_key: this.openRouterApiKey
    });
  }

  async getSuggestions(
    description: string,
    context?: CommandContext
  ): Promise<CommandSuggestionResponse> {
    return this.client.ai.suggestCommand({
      api_key: this.openRouterApiKey,
      description,
      current_directory: context?.currentDirectory || '/home/user',
      shell_type: context?.shellType || 'bash',
      os_type: context?.osType || 'linux',
      max_suggestions: 3,
      include_explanations: true,
      preferred_model: 'google/gemini-2.5-flash'
    });
  }

  async explainCommand(command: string): Promise<CommandExplanationResponse> {
    return this.client.ai.explainCommand({
      api_key: this.openRouterApiKey,
      command,
      detail_level: 'detailed'
    });
  }

  async analyzeError(
    command: string,
    errorOutput: string,
    exitCode?: number
  ): Promise<ErrorAnalysisResponse> {
    return this.client.ai.explainError({
      api_key: this.openRouterApiKey,
      command,
      error_output: errorOutput,
      exit_code: exitCode
    });
  }

  async optimizeCommand(
    command: string,
    context?: CommandContext
  ): Promise<CommandOptimizationResponse> {
    return this.client.ai.optimizeCommand({
      api_key: this.openRouterApiKey,
      command,
      context: {
        shell_type: context?.shellType || 'bash',
        os_type: context?.osType || 'linux',
        performance_priority: 'balanced'
      }
    });
  }
}

interface CommandContext {
  currentDirectory?: string;
  shellType?: 'bash' | 'zsh' | 'fish' | 'powershell';
  osType?: 'linux' | 'macos' | 'windows';
}

// Usage example
const aiAssistant = new AICommandAssistant(
  authenticatedClient,
  'sk-or-v1-your-openrouter-key'
);

// Validate API key first
const validation = await aiAssistant.validateApiKey();
if (!validation.valid) {
  throw new Error(`Invalid API key: ${validation.error}`);
}

// Get command suggestions
const suggestions = await aiAssistant.getSuggestions(
  'Find all Python files larger than 1MB in the current directory',
  {
    currentDirectory: '/home/user/projects',
    shellType: 'bash',
    osType: 'linux'
  }
);

console.log('AI Suggestions:');
suggestions.suggestions.forEach((suggestion, index) => {
  console.log(`${index + 1}. ${suggestion.command}`);
  console.log(`   ${suggestion.description}`);
  console.log(`   Safety: ${suggestion.safety_level}`);
  console.log(`   Confidence: ${(suggestion.confidence_score * 100).toFixed(1)}%`);
});

// Analyze an error
const errorAnalysis = await aiAssistant.analyzeError(
  'npm install',
  'npm ERR! code EACCES\nnpm ERR! syscall mkdir',
  1
);

console.log('Error Analysis:', errorAnalysis.error_analysis);
console.log('Solutions:');
errorAnalysis.solutions.forEach((solution, index) => {
  console.log(`${index + 1}. ${solution.solution}`);
  console.log(`   Command: ${solution.command}`);
  console.log(`   Risk: ${solution.risk_level}`);
});
```

### 5. Command History Management

```typescript
class CommandHistoryManager {
  constructor(private client: DevPocketClient) {}

  async getHistory(filters?: {
    limit?: number;
    offset?: number;
    sessionId?: string;
    status?: 'completed' | 'failed' | 'cancelled';
    search?: string;
    startDate?: Date;
    endDate?: Date;
  }): Promise<{ commands: Command[]; total: number; hasMore: boolean }> {
    const params: any = {};
    
    if (filters?.limit) params.limit = filters.limit;
    if (filters?.offset) params.offset = filters.offset;
    if (filters?.sessionId) params.session_id = filters.sessionId;
    if (filters?.status) params.status = filters.status;
    if (filters?.search) params.search = filters.search;
    if (filters?.startDate) params.start_date = filters.startDate.toISOString();
    if (filters?.endDate) params.end_date = filters.endDate.toISOString();

    return this.client.commands.list(params);
  }

  async searchCommands(query: string, includeOutput = false): Promise<Command[]> {
    const response = await this.client.commands.search({
      q: query,
      include_output: includeOutput,
      limit: 50
    });
    
    return response.commands;
  }

  async getCommand(commandId: string): Promise<Command> {
    return this.client.commands.get(commandId);
  }

  async getStats(): Promise<CommandStats> {
    const response = await this.getHistory({ limit: 1000 });
    
    const stats = {
      totalCommands: response.total,
      successfulCommands: 0,
      failedCommands: 0,
      mostUsedCommands: new Map<string, number>(),
      averageExecutionTime: 0,
      totalExecutionTime: 0
    };

    let totalTime = 0;
    let commandsWithTime = 0;

    response.commands.forEach(cmd => {
      // Count by status
      if (cmd.status === 'completed' && cmd.exit_code === 0) {
        stats.successfulCommands++;
      } else if (cmd.status === 'failed' || cmd.exit_code !== 0) {
        stats.failedCommands++;
      }

      // Track command usage
      const baseCommand = cmd.command_text.split(' ')[0];
      const count = stats.mostUsedCommands.get(baseCommand) || 0;
      stats.mostUsedCommands.set(baseCommand, count + 1);

      // Calculate average execution time
      if (cmd.execution_time_ms) {
        totalTime += cmd.execution_time_ms;
        commandsWithTime++;
      }
    });

    if (commandsWithTime > 0) {
      stats.averageExecutionTime = totalTime / commandsWithTime;
    }
    stats.totalExecutionTime = totalTime;

    return stats;
  }
}

interface CommandStats {
  totalCommands: number;
  successfulCommands: number;
  failedCommands: number;
  mostUsedCommands: Map<string, number>;
  averageExecutionTime: number;
  totalExecutionTime: number;
}

// Usage example
const historyManager = new CommandHistoryManager(authenticatedClient);

// Get recent commands
const recentCommands = await historyManager.getHistory({
  limit: 20,
  status: 'completed'
});

console.log(`Found ${recentCommands.total} commands`);
recentCommands.commands.forEach(cmd => {
  console.log(`${cmd.created_at}: ${cmd.command_text} (${cmd.exit_code})`);
});

// Search command history
const gitCommands = await historyManager.searchCommands('git commit');
console.log(`Found ${gitCommands.length} git commit commands`);

// Get usage statistics
const stats = await historyManager.getStats();
console.log(`Success rate: ${(stats.successfulCommands / stats.totalCommands * 100).toFixed(1)}%`);
console.log(`Average execution time: ${stats.averageExecutionTime.toFixed(0)}ms`);

// Show most used commands
const topCommands = Array.from(stats.mostUsedCommands.entries())
  .sort((a, b) => b[1] - a[1])
  .slice(0, 5);

console.log('Most used commands:');
topCommands.forEach(([cmd, count]) => {
  console.log(`  ${cmd}: ${count} times`);
});
```

## Advanced Integration

### 1. Multi-Device Synchronization

```typescript
class SyncManager {
  constructor(private client: DevPocketClient) {}

  async getSyncStatus(): Promise<SyncStatus> {
    return this.client.sync.getStatus();
  }

  async triggerSync(options?: {
    dataTypes?: string[];
    force?: boolean;
  }): Promise<SyncOperation> {
    return this.client.sync.trigger(options);
  }

  async getConflicts(): Promise<SyncConflict[]> {
    const response = await this.client.sync.getConflicts();
    return response.conflicts;
  }

  async resolveConflict(
    conflictId: string,
    resolution: {
      type: 'keep_device' | 'keep_latest' | 'merge' | 'custom';
      chosenDeviceId?: string;
      mergedData?: any;
    }
  ): Promise<ConflictResolution> {
    return this.client.sync.resolveConflict(conflictId, {
      resolution_type: resolution.type,
      chosen_device_id: resolution.chosenDeviceId,
      merged_data: resolution.mergedData
    });
  }

  async enableAutoSync(dataTypes: string[] = ['all']): Promise<void> {
    // Set up automatic sync polling
    setInterval(async () => {
      try {
        const status = await this.getSyncStatus();
        if (status.pending_changes > 0) {
          await this.triggerSync({ dataTypes });
        }
      } catch (error) {
        console.warn('Auto-sync failed:', error);
      }
    }, 30000); // Sync every 30 seconds
  }
}

// Usage example
const syncManager = new SyncManager(authenticatedClient);

// Check sync status
const status = await syncManager.getSyncStatus();
console.log(`Last sync: ${status.last_sync}`);
console.log(`Pending changes: ${status.pending_changes}`);

// Handle conflicts
const conflicts = await syncManager.getConflicts();
if (conflicts.length > 0) {
  console.log(`Found ${conflicts.length} sync conflicts`);
  
  for (const conflict of conflicts) {
    // Auto-resolve by keeping latest version
    await syncManager.resolveConflict(conflict.id, {
      type: 'keep_latest'
    });
  }
}

// Enable automatic synchronization
await syncManager.enableAutoSync(['ssh_profiles', 'settings']);
```

### 2. Real-Time Notifications

```typescript
class NotificationManager {
  private eventSource: EventSource | null = null;

  constructor(private client: DevPocketClient, private accessToken: string) {}

  async subscribeToNotifications(
    types: string[] = ['all'],
    callback: (notification: Notification) => void
  ): Promise<void> {
    const url = new URL('/api/notifications/stream', this.client.apiUrl);
    url.searchParams.set('token', this.accessToken);
    url.searchParams.set('types', types.join(','));

    this.eventSource = new EventSource(url.toString());

    this.eventSource.onmessage = (event) => {
      try {
        const notification = JSON.parse(event.data);
        callback(notification);
      } catch (error) {
        console.error('Failed to parse notification:', error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('Notification stream error:', error);
      this.handleReconnection();
    };
  }

  private handleReconnection(): void {
    setTimeout(() => {
      if (this.eventSource) {
        this.eventSource.close();
        // Implement reconnection logic
      }
    }, 5000);
  }

  unsubscribe(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

interface Notification {
  id: string;
  type: 'sync_complete' | 'session_ended' | 'ai_quota_warning' | 'security_alert';
  title: string;
  message: string;
  data?: any;
  timestamp: string;
}

// Usage example
const notificationManager = new NotificationManager(client, accessToken);

await notificationManager.subscribeToNotifications(['sync', 'security'], (notification) => {
  console.log(`📱 ${notification.title}: ${notification.message}`);
  
  // Handle specific notification types
  switch (notification.type) {
    case 'sync_complete':
      console.log('✅ Sync completed successfully');
      break;
    case 'security_alert':
      console.warn('🚨 Security alert:', notification.data);
      break;
    case 'ai_quota_warning':
      console.warn('⚠️ AI quota warning:', notification.message);
      break;
  }
});
```

### 3. Batch Operations

```typescript
class BatchOperations {
  constructor(private client: DevPocketClient) {}

  async batchCreateSSHProfiles(profiles: CreateSSHProfileRequest[]): Promise<SSHProfile[]> {
    const results: SSHProfile[] = [];
    const batchSize = 5; // Process in batches to avoid rate limits

    for (let i = 0; i < profiles.length; i += batchSize) {
      const batch = profiles.slice(i, i + batchSize);
      
      const batchPromises = batch.map(profile => 
        this.client.ssh.profiles.create(profile)
          .catch(error => ({ error, profile }))
      );

      const batchResults = await Promise.all(batchPromises);
      
      batchResults.forEach(result => {
        if ('error' in result) {
          console.error('Failed to create profile:', result.error);
        } else {
          results.push(result);
        }
      });

      // Add delay between batches
      if (i + batchSize < profiles.length) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    return results;
  }

  async batchAIRequests(requests: AIRequest[]): Promise<AIResponse[]> {
    return this.client.ai.batch({
      requests,
      max_concurrent: 3,
      timeout_seconds: 30
    });
  }

  async bulkCommandHistory(
    commands: Array<{
      command: string;
      sessionId: string;
      timestamp: Date;
    }>
  ): Promise<void> {
    // Batch insert command history
    const batchSize = 50;
    
    for (let i = 0; i < commands.length; i += batchSize) {
      const batch = commands.slice(i, i + batchSize);
      
      await this.client.commands.bulkCreate({
        commands: batch.map(cmd => ({
          command_text: cmd.command,
          session_id: cmd.sessionId,
          created_at: cmd.timestamp.toISOString()
        }))
      });
    }
  }
}

interface AIRequest {
  type: 'suggest' | 'explain' | 'analyze_error';
  data: any;
}

interface AIResponse {
  success: boolean;
  data?: any;
  error?: string;
}

// Usage example
const batchOps = new BatchOperations(authenticatedClient);

// Batch create SSH profiles
const profilesData = [
  {
    name: 'Server 1',
    hostname: 'server1.example.com',
    username: 'admin',
    auth_method: 'key' as const,
    ssh_key_id: 'key1'
  },
  {
    name: 'Server 2',
    hostname: 'server2.example.com',
    username: 'deploy',
    auth_method: 'password' as const,
    password: 'secure123'
  }
];

const createdProfiles = await batchOps.batchCreateSSHProfiles(profilesData);
console.log(`Created ${createdProfiles.length} SSH profiles`);

// Batch AI requests
const aiRequests: AIRequest[] = [
  {
    type: 'suggest',
    data: {
      description: 'List all running processes',
      shell_type: 'bash'
    }
  },
  {
    type: 'explain',
    data: {
      command: 'grep -r "TODO" .'
    }
  }
];

const aiResponses = await batchOps.batchAIRequests(aiRequests);
console.log(`Processed ${aiResponses.length} AI requests`);
```

## Platform-Specific Examples

### React Web Application

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { DevPocketClient } from '@devpocket/api-client';

// Context for auth state
const AuthContext = React.createContext<{
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}>({
  user: null,
  login: async () => {},
  logout: async () => {},
  isAuthenticated: false
});

// Auth provider component
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [client] = useState(() => new DevPocketClient({
    apiUrl: process.env.REACT_APP_API_URL || 'https://api.devpocket.app'
  }));

  const login = useCallback(async (username: string, password: string) => {
    try {
      const response = await client.auth.login({ username, password });
      setUser(response.user);
      
      // Store tokens securely
      sessionStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }, [client]);

  const logout = useCallback(async () => {
    try {
      await client.auth.logout();
    } catch (error) {
      console.warn('Logout request failed:', error);
    } finally {
      setUser(null);
      sessionStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }, [client]);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = sessionStorage.getItem('access_token');
      if (token) {
        try {
          client.setAccessToken(token);
          const userData = await client.auth.getCurrentUser();
          setUser(userData);
        } catch (error) {
          console.error('Auth check failed:', error);
          await logout();
        }
      }
    };

    checkAuth();
  }, [client, logout]);

  return (
    <AuthContext.Provider value={{
      user,
      login,
      logout,
      isAuthenticated: user !== null
    }}>
      {children}
    </AuthContext.Provider>
  );
};

// Terminal component
export const Terminal: React.FC = () => {
  const [terminalWS, setTerminalWS] = useState<TerminalWebSocket | null>(null);
  const [output, setOutput] = useState<string>('');
  const [input, setInput] = useState<string>('');
  const [sessionId, setSessionId] = useState<string | null>(null);

  const { user } = useContext(AuthContext);

  useEffect(() => {
    if (!user) return;

    const initTerminal = async () => {
      try {
        const ws = new TerminalWebSocket(
          process.env.REACT_APP_WS_URL || 'wss://api.devpocket.app',
          sessionStorage.getItem('access_token')!,
          'web-client'
        );

        await ws.connect();

        ws.onOutput((data) => {
          setOutput(prev => prev + data);
        });

        ws.onStatus((status) => {
          console.log('Terminal status:', status);
        });

        ws.onError((error) => {
          console.error('Terminal error:', error);
        });

        setTerminalWS(ws);
      } catch (error) {
        console.error('Failed to initialize terminal:', error);
      }
    };

    initTerminal();

    return () => {
      terminalWS?.disconnect();
    };
  }, [user]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (terminalWS && sessionId && input.trim()) {
      terminalWS.sendInput(input + '\n');
      setInput('');
    }
  }, [terminalWS, sessionId, input]);

  const createSession = useCallback(async () => {
    if (!terminalWS) return;

    try {
      const id = await terminalWS.createSSHSession(
        'your-ssh-profile-id',
        { rows: 24, cols: 80 }
      );
      setSessionId(id);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  }, [terminalWS]);

  return (
    <div className="terminal-container">
      <div className="terminal-header">
        <button onClick={createSession} disabled={!terminalWS || !!sessionId}>
          {sessionId ? 'Connected' : 'Connect to SSH'}
        </button>
      </div>
      
      <div className="terminal-output">
        <pre>{output}</pre>
      </div>
      
      <form onSubmit={handleSubmit} className="terminal-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter command..."
          disabled={!sessionId}
        />
        <button type="submit" disabled={!sessionId || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
};

// SSH Profile Manager component
export const SSHProfileManager: React.FC = () => {
  const [profiles, setProfiles] = useState<SSHProfile[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const { user } = useContext(AuthContext);

  useEffect(() => {
    if (!user) return;

    const loadProfiles = async () => {
      try {
        const client = new DevPocketClient({
          apiUrl: process.env.REACT_APP_API_URL!,
          accessToken: sessionStorage.getItem('access_token')!
        });

        const response = await client.ssh.profiles.list();
        setProfiles(response.profiles);
      } catch (error) {
        console.error('Failed to load SSH profiles:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadProfiles();
  }, [user]);

  if (isLoading) {
    return <div>Loading SSH profiles...</div>;
  }

  return (
    <div className="ssh-profiles">
      <h2>SSH Profiles</h2>
      
      {profiles.length === 0 ? (
        <p>No SSH profiles found. Create one to get started.</p>
      ) : (
        <ul>
          {profiles.map(profile => (
            <li key={profile.id}>
              <strong>{profile.name}</strong> - {profile.hostname}:{profile.port}
              <span>({profile.username})</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
```

### Flutter Mobile Application

```dart
// lib/services/devpocket_service.dart
import 'package:flutter/foundation.dart';
import 'package:devpocket_api/devpocket_api.dart';

class DevPocketService extends ChangeNotifier {
  late DevPocketClient _client;
  User? _user;
  bool _isAuthenticated = false;

  DevPocketService() {
    _client = DevPocketClient(
      apiUrl: kDebugMode 
        ? 'http://localhost:8000'
        : 'https://api.devpocket.app',
    );
  }

  User? get user => _user;
  bool get isAuthenticated => _isAuthenticated;
  DevPocketClient get client => _client;

  Future<void> login(String username, String password) async {
    try {
      final response = await _client.auth.login(
        username: username,
        password: password,
      );

      _user = response.user;
      _isAuthenticated = true;
      
      // Store tokens securely
      await _storeTokens(response.accessToken, response.refreshToken);
      
      notifyListeners();
    } catch (error) {
      print('Login failed: $error');
      rethrow;
    }
  }

  Future<void> logout() async {
    try {
      await _client.auth.logout();
    } catch (error) {
      print('Logout request failed: $error');
    }

    _user = null;
    _isAuthenticated = false;
    await _clearTokens();
    
    notifyListeners();
  }

  Future<void> checkAuthStatus() async {
    final accessToken = await _getStoredToken('access_token');
    if (accessToken != null) {
      try {
        _client.setAccessToken(accessToken);
        _user = await _client.auth.getCurrentUser();
        _isAuthenticated = true;
        notifyListeners();
      } catch (error) {
        print('Auth check failed: $error');
        await logout();
      }
    }
  }

  Future<void> _storeTokens(String accessToken, String refreshToken) async {
    // Use flutter_secure_storage for secure token storage
    const storage = FlutterSecureStorage();
    await storage.write(key: 'access_token', value: accessToken);
    await storage.write(key: 'refresh_token', value: refreshToken);
  }

  Future<String?> _getStoredToken(String key) async {
    const storage = FlutterSecureStorage();
    return await storage.read(key: key);
  }

  Future<void> _clearTokens() async {
    const storage = FlutterSecureStorage();
    await storage.delete(key: 'access_token');
    await storage.delete(key: 'refresh_token');
  }
}

// lib/screens/terminal_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

class TerminalScreen extends StatefulWidget {
  @override
  _TerminalScreenState createState() => _TerminalScreenState();
}

class _TerminalScreenState extends State<TerminalScreen> {
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  String _output = '';
  DevPocketWebSocket? _websocket;
  String? _sessionId;

  @override
  void initState() {
    super.initState();
    _initializeWebSocket();
  }

  Future<void> _initializeWebSocket() async {
    final service = Provider.of<DevPocketService>(context, listen: false);
    
    if (!service.isAuthenticated) return;

    try {
      final accessToken = await service._getStoredToken('access_token');
      
      _websocket = DevPocketWebSocket(
        service.client.apiUrl,
        accessToken!,
      );

      await _websocket!.connect();

      _websocket!.onOutput((output) {
        setState(() {
          _output += output;
        });
        _scrollToBottom();
      });

      _websocket!.onError((error) {
        _showError('Terminal error: ${error['message']}');
      });

    } catch (error) {
      _showError('Failed to connect to terminal: $error');
    }
  }

  Future<void> _createSession(String sshProfileId) async {
    if (_websocket == null) return;

    try {
      final sessionId = await _websocket!.createSSHSession(
        sshProfileId,
        {'rows': 24, 'cols': 80},
      );

      setState(() {
        _sessionId = sessionId;
      });

      _showMessage('SSH session created successfully');
    } catch (error) {
      _showError('Failed to create SSH session: $error');
    }
  }

  void _sendInput() {
    if (_websocket == null || _sessionId == null) return;

    final input = _inputController.text;
    if (input.isNotEmpty) {
      _websocket!.sendInput(input + '\n');
      _inputController.clear();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: Duration(milliseconds: 100),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Terminal'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _initializeWebSocket,
          ),
        ],
      ),
      body: Column(
        children: [
          // Connection status
          Container(
            padding: EdgeInsets.all(8),
            color: _sessionId != null ? Colors.green : Colors.orange,
            child: Row(
              children: [
                Icon(
                  _sessionId != null ? Icons.check_circle : Icons.warning,
                  color: Colors.white,
                ),
                SizedBox(width: 8),
                Text(
                  _sessionId != null ? 'Connected' : 'Not connected',
                  style: TextStyle(color: Colors.white),
                ),
              ],
            ),
          ),
          
          // Terminal output
          Expanded(
            child: Container(
              color: Colors.black,
              padding: EdgeInsets.all(8),
              child: SingleChildScrollView(
                controller: _scrollController,
                child: Text(
                  _output,
                  style: TextStyle(
                    color: Colors.green,
                    fontFamily: 'monospace',
                    fontSize: 12,
                  ),
                ),
              ),
            ),
          ),
          
          // Input area
          Container(
            padding: EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputController,
                    decoration: InputDecoration(
                      hintText: 'Enter command...',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _sendInput(),
                    enabled: _sessionId != null,
                  ),
                ),
                SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _sessionId != null ? _sendInput : null,
                  child: Text('Send'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _websocket?.disconnect();
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}
```

### Node.js Server Application

```typescript
// server.ts
import express from 'express';
import { DevPocketClient } from '@devpocket/api-client';

const app = express();
app.use(express.json());

const devpocketClient = new DevPocketClient({
  apiUrl: process.env.DEVPOCKET_API_URL || 'https://api.devpocket.app',
  apiKey: process.env.DEVPOCKET_API_KEY, // Server-side API key
});

// Middleware to authenticate users
async function authenticateUser(req: any, res: any, next: any) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid authorization header' });
  }

  const token = authHeader.substring(7);
  
  try {
    // Verify token with DevPocket API
    const userClient = new DevPocketClient({
      apiUrl: process.env.DEVPOCKET_API_URL!,
      accessToken: token,
    });

    const user = await userClient.auth.getCurrentUser();
    req.user = user;
    req.devpocketClient = userClient;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// Create SSH profile via server
app.post('/api/server/ssh-profiles', authenticateUser, async (req, res) => {
  try {
    const profile = await req.devpocketClient.ssh.profiles.create(req.body);
    res.json(profile);
  } catch (error) {
    console.error('Failed to create SSH profile:', error);
    res.status(500).json({ error: 'Failed to create SSH profile' });
  }
});

// Get user's terminal sessions
app.get('/api/server/sessions', authenticateUser, async (req, res) => {
  try {
    const sessions = await req.devpocketClient.sessions.list();
    res.json(sessions);
  } catch (error) {
    console.error('Failed to get sessions:', error);
    res.status(500).json({ error: 'Failed to get sessions' });
  }
});

// Bulk operations endpoint
app.post('/api/server/bulk-operations', authenticateUser, async (req, res) => {
  const { operation, data } = req.body;

  try {
    let result;
    
    switch (operation) {
      case 'create_ssh_profiles':
        result = await Promise.all(
          data.map((profile: any) => 
            req.devpocketClient.ssh.profiles.create(profile)
          )
        );
        break;
      
      case 'ai_batch':
        result = await req.devpocketClient.ai.batch({
          requests: data.requests,
          api_key: data.openrouter_key,
        });
        break;
      
      default:
        return res.status(400).json({ error: 'Unknown operation' });
    }

    res.json({ success: true, result });
  } catch (error) {
    console.error('Bulk operation failed:', error);
    res.status(500).json({ error: 'Bulk operation failed' });
  }
});

// Webhook endpoint for DevPocket events
app.post('/webhook/devpocket', express.raw({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-devpocket-signature'] as string;
  
  // Verify webhook signature (implementation depends on your setup)
  if (!verifyWebhookSignature(req.body, signature)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const event = JSON.parse(req.body.toString());
  
  // Handle different event types
  switch (event.type) {
    case 'session.created':
      console.log('New session created:', event.data.session_id);
      break;
    
    case 'sync.completed':
      console.log('Sync completed for user:', event.data.user_id);
      break;
    
    case 'ai.quota_exceeded':
      console.log('AI quota exceeded for user:', event.data.user_id);
      // Send notification to user
      break;
  }

  res.json({ received: true });
});

function verifyWebhookSignature(payload: Buffer, signature: string): boolean {
  // Implementation for webhook signature verification
  // This would typically use HMAC with a shared secret
  return true; // Simplified for example
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

## Testing and Debugging

### Unit Testing

```typescript
// __tests__/devpocket-client.test.ts
import { DevPocketClient } from '@devpocket/api-client';
import { setupMockServer } from './mock-server';

describe('DevPocket Client', () => {
  let client: DevPocketClient;
  let mockServer: any;

  beforeAll(async () => {
    mockServer = await setupMockServer();
    client = new DevPocketClient({
      apiUrl: mockServer.url,
    });
  });

  afterAll(async () => {
    await mockServer.close();
  });

  describe('Authentication', () => {
    it('should login successfully', async () => {
      const response = await client.auth.login({
        username: 'test@example.com',
        password: 'testpassword',
      });

      expect(response.access_token).toBeDefined();
      expect(response.user.email).toBe('test@example.com');
    });

    it('should handle login failure', async () => {
      await expect(
        client.auth.login({
          username: 'invalid@example.com',
          password: 'wrongpassword',
        })
      ).rejects.toThrow('Invalid credentials');
    });

    it('should refresh token', async () => {
      // First login
      const loginResponse = await client.auth.login({
        username: 'test@example.com',
        password: 'testpassword',
      });

      // Then refresh
      const refreshResponse = await client.auth.refresh({
        refresh_token: loginResponse.refresh_token,
      });

      expect(refreshResponse.access_token).toBeDefined();
      expect(refreshResponse.access_token).not.toBe(loginResponse.access_token);
    });
  });

  describe('SSH Profiles', () => {
    let accessToken: string;

    beforeEach(async () => {
      const loginResponse = await client.auth.login({
        username: 'test@example.com',
        password: 'testpassword',
      });
      accessToken = loginResponse.access_token;
      client.setAccessToken(accessToken);
    });

    it('should create SSH profile', async () => {
      const profile = await client.ssh.profiles.create({
        name: 'Test Server',
        hostname: 'test.example.com',
        username: 'testuser',
        auth_method: 'password',
        password: 'testpass',
      });

      expect(profile.id).toBeDefined();
      expect(profile.name).toBe('Test Server');
      expect(profile.hostname).toBe('test.example.com');
    });

    it('should list SSH profiles', async () => {
      const response = await client.ssh.profiles.list();
      expect(response.profiles).toBeInstanceOf(Array);
    });

    it('should test SSH connection', async () => {
      const profile = await client.ssh.profiles.create({
        name: 'Test Server',
        hostname: 'test.example.com',
        username: 'testuser',
        auth_method: 'password',
        password: 'testpass',
      });

      const testResult = await client.ssh.profiles.test(profile.id);
      expect(testResult.success).toBeDefined();
    });
  });

  describe('WebSocket Terminal', () => {
    it('should establish WebSocket connection', async () => {
      // This would require a more complex setup with WebSocket mocking
      // Using libraries like 'mock-socket' or similar
      const mockWS = new MockWebSocket();
      const terminal = new TerminalWebSocket(mockServer.wsUrl, 'mock-token');
      
      await terminal.connect();
      expect(mockWS.readyState).toBe(WebSocket.OPEN);
    });
  });
});

// __tests__/mock-server.ts
import { setupServer } from 'msw/node';
import { rest } from 'msw';

export function setupMockServer() {
  const handlers = [
    // Auth endpoints
    rest.post('/api/auth/login', (req, res, ctx) => {
      const { username, password } = req.body as any;
      
      if (username === 'test@example.com' && password === 'testpassword') {
        return res(ctx.json({
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: 'user-123',
            email: 'test@example.com',
            username: 'testuser',
            subscription_tier: 'pro',
          },
        }));
      }
      
      return res(
        ctx.status(401),
        ctx.json({ error: { message: 'Invalid credentials' } })
      );
    }),

    rest.post('/api/auth/refresh', (req, res, ctx) => {
      return res(ctx.json({
        access_token: 'new-mock-access-token',
        token_type: 'bearer',
        expires_in: 3600,
      }));
    }),

    // SSH Profile endpoints
    rest.post('/api/ssh/profiles', (req, res, ctx) => {
      const profile = req.body as any;
      return res(ctx.json({
        id: 'profile-123',
        ...profile,
        created_at: '2023-01-01T12:00:00Z',
      }));
    }),

    rest.get('/api/ssh/profiles', (req, res, ctx) => {
      return res(ctx.json({
        profiles: [],
        total: 0,
      }));
    }),

    rest.post('/api/ssh/profiles/:id/test', (req, res, ctx) => {
      return res(ctx.json({
        success: true,
        connection_time_ms: 250,
        message: 'Connection successful',
      }));
    }),
  ];

  const server = setupServer(...handlers);
  
  return {
    server,
    url: 'http://localhost:3000',
    wsUrl: 'ws://localhost:3000',
    close: () => server.close(),
  };
}
```

### Integration Testing

```typescript
// __tests__/integration.test.ts
describe('DevPocket Integration Tests', () => {
  let client: DevPocketClient;
  
  beforeAll(() => {
    client = new DevPocketClient({
      apiUrl: process.env.TEST_API_URL || 'http://localhost:8000',
    });
  });

  describe('Full Authentication Flow', () => {
    it('should complete registration -> login -> profile operations', async () => {
      const timestamp = Date.now();
      const email = `test${timestamp}@example.com`;
      const username = `testuser${timestamp}`;
      
      // 1. Register
      const registerResponse = await client.auth.register({
        email,
        username,
        password: 'TestPass123!',
        display_name: 'Test User',
      });

      expect(registerResponse.user.email).toBe(email);
      client.setAccessToken(registerResponse.access_token);

      // 2. Get current user
      const currentUser = await client.auth.getCurrentUser();
      expect(currentUser.id).toBe(registerResponse.user.id);

      // 3. Create SSH profile
      const sshProfile = await client.ssh.profiles.create({
        name: 'Integration Test Server',
        hostname: 'test.example.com',
        username: 'testuser',
        auth_method: 'password',
        password: 'testpass',
      });

      expect(sshProfile.name).toBe('Integration Test Server');

      // 4. List profiles
      const profilesResponse = await client.ssh.profiles.list();
      expect(profilesResponse.profiles).toContainEqual(
        expect.objectContaining({ id: sshProfile.id })
      );

      // 5. Create terminal session
      const session = await client.sessions.create({
        name: 'Test Session',
        session_type: 'ssh',
        ssh_profile_id: sshProfile.id,
      });

      expect(session.ssh_profile_id).toBe(sshProfile.id);

      // 6. Cleanup
      await client.sessions.delete(session.id);
      await client.ssh.profiles.delete(sshProfile.id);
    });
  });

  describe('AI Services Integration', () => {
    it('should validate and use OpenRouter API key', async () => {
      const openRouterKey = process.env.TEST_OPENROUTER_KEY;
      if (!openRouterKey) {
        console.log('Skipping AI tests - no OpenRouter key provided');
        return;
      }

      // Login first
      const loginResponse = await client.auth.login({
        username: process.env.TEST_USERNAME!,
        password: process.env.TEST_PASSWORD!,
      });
      client.setAccessToken(loginResponse.access_token);

      // Validate API key
      const validation = await client.ai.validateKey({
        api_key: openRouterKey,
      });
      expect(validation.valid).toBe(true);

      // Get command suggestions
      const suggestions = await client.ai.suggestCommand({
        api_key: openRouterKey,
        description: 'List all files in current directory',
        shell_type: 'bash',
        os_type: 'linux',
      });

      expect(suggestions.suggestions.length).toBeGreaterThan(0);
      expect(suggestions.suggestions[0].command).toContain('ls');
    });
  });
});
```

### Performance Testing

```typescript
// __tests__/performance.test.ts
describe('Performance Tests', () => {
  let client: DevPocketClient;

  beforeAll(async () => {
    client = new DevPocketClient({
      apiUrl: process.env.TEST_API_URL || 'http://localhost:8000',
    });

    // Login for authenticated tests
    const loginResponse = await client.auth.login({
      username: process.env.TEST_USERNAME!,
      password: process.env.TEST_PASSWORD!,
    });
    client.setAccessToken(loginResponse.access_token);
  });

  it('should handle concurrent SSH profile creation', async () => {
    const startTime = Date.now();
    const concurrentOperations = 10;

    const promises = Array.from({ length: concurrentOperations }, (_, i) =>
      client.ssh.profiles.create({
        name: `Perf Test Server ${i}`,
        hostname: `server${i}.example.com`,
        username: 'testuser',
        auth_method: 'password',
        password: 'testpass',
      })
    );

    const results = await Promise.all(promises);
    const endTime = Date.now();

    expect(results).toHaveLength(concurrentOperations);
    expect(endTime - startTime).toBeLessThan(5000); // Should complete within 5 seconds

    // Cleanup
    await Promise.all(
      results.map(profile => client.ssh.profiles.delete(profile.id))
    );
  });

  it('should handle pagination efficiently', async () => {
    // Create test data
    const profiles = await Promise.all(
      Array.from({ length: 25 }, (_, i) =>
        client.ssh.profiles.create({
          name: `Pagination Test ${i}`,
          hostname: `server${i}.example.com`,
          username: 'testuser',
          auth_method: 'password',
          password: 'testpass',
        })
      )
    );

    try {
      // Test pagination
      const page1 = await client.ssh.profiles.list({ limit: 10, offset: 0 });
      const page2 = await client.ssh.profiles.list({ limit: 10, offset: 10 });
      const page3 = await client.ssh.profiles.list({ limit: 10, offset: 20 });

      expect(page1.profiles).toHaveLength(10);
      expect(page2.profiles).toHaveLength(10);
      expect(page3.profiles).toHaveLength(5);

      // Verify no duplicates across pages
      const allIds = [
        ...page1.profiles.map(p => p.id),
        ...page2.profiles.map(p => p.id),
        ...page3.profiles.map(p => p.id),
      ];
      const uniqueIds = new Set(allIds);
      expect(uniqueIds.size).toBe(allIds.length);

    } finally {
      // Cleanup
      await Promise.all(
        profiles.map(profile => client.ssh.profiles.delete(profile.id))
      );
    }
  });
});
```

## Production Deployment

### Environment Configuration

```typescript
// config/production.ts
export const productionConfig = {
  apiUrl: 'https://api.devpocket.app',
  wsUrl: 'wss://api.devpocket.app',
  
  // Security settings
  enableSSL: true,
  validateCertificates: true,
  
  // Performance settings
  requestTimeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
  
  // Caching
  enableResponseCache: true,
  cacheMaxAge: 300, // 5 minutes
  
  // Logging
  logLevel: 'warn',
  enableTelemetry: true,
  
  // Rate limiting
  rateLimitPerMinute: 100,
  burstLimit: 200,
};

// config/staging.ts
export const stagingConfig = {
  ...productionConfig,
  apiUrl: 'https://staging-api.devpocket.app',
  wsUrl: 'wss://staging-api.devpocket.app',
  logLevel: 'info',
  enableTelemetry: false,
};

// config/development.ts
export const developmentConfig = {
  apiUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000',
  enableSSL: false,
  validateCertificates: false,
  requestTimeout: 10000,
  retryAttempts: 1,
  logLevel: 'debug',
  enableTelemetry: false,
  rateLimitPerMinute: 1000,
};
```

### Error Handling and Monitoring

```typescript
// utils/error-handler.ts
export class DevPocketError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'DevPocketError';
  }

  static fromApiError(error: any): DevPocketError {
    return new DevPocketError(
      error.message || 'An error occurred',
      error.code || 'unknown_error',
      error.statusCode,
      error.details
    );
  }
}

export class ErrorReporter {
  private static instance: ErrorReporter;
  
  static getInstance(): ErrorReporter {
    if (!ErrorReporter.instance) {
      ErrorReporter.instance = new ErrorReporter();
    }
    return ErrorReporter.instance;
  }

  reportError(error: Error, context?: any): void {
    // Log error
    console.error('DevPocket Error:', {
      message: error.message,
      stack: error.stack,
      context,
      timestamp: new Date().toISOString(),
    });

    // Send to monitoring service (e.g., Sentry, DataDog)
    if (process.env.NODE_ENV === 'production') {
      this.sendToMonitoring(error, context);
    }
  }

  private sendToMonitoring(error: Error, context?: any): void {
    // Implementation for your monitoring service
    // Example with Sentry:
    // Sentry.captureException(error, { extra: context });
  }
}

// Usage in client
const client = new DevPocketClient({
  apiUrl: config.apiUrl,
  onError: (error) => {
    ErrorReporter.getInstance().reportError(error);
  },
});
```

### Health Monitoring

```typescript
// utils/health-monitor.ts
export class HealthMonitor {
  private isHealthy = true;
  private lastHealthCheck = Date.now();
  private healthCheckInterval: NodeJS.Timeout | null = null;

  constructor(private client: DevPocketClient) {}

  startMonitoring(intervalMs = 60000): void {
    this.healthCheckInterval = setInterval(() => {
      this.performHealthCheck();
    }, intervalMs);
  }

  stopMonitoring(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  private async performHealthCheck(): Promise<void> {
    try {
      const startTime = Date.now();
      await this.client.health.check();
      const responseTime = Date.now() - startTime;

      this.isHealthy = true;
      this.lastHealthCheck = Date.now();

      // Report metrics
      this.reportMetrics({
        healthy: true,
        responseTime,
        timestamp: this.lastHealthCheck,
      });

    } catch (error) {
      this.isHealthy = false;
      
      console.error('Health check failed:', error);
      
      this.reportMetrics({
        healthy: false,
        error: error.message,
        timestamp: Date.now(),
      });
    }
  }

  private reportMetrics(metrics: any): void {
    // Send metrics to monitoring service
    // Example: send to CloudWatch, DataDog, etc.
  }

  getHealthStatus(): { healthy: boolean; lastCheck: number } {
    return {
      healthy: this.isHealthy,
      lastCheck: this.lastHealthCheck,
    };
  }
}
```

### Deployment Checklist

1. **Environment Variables**
   ```bash
   # Required
   DEVPOCKET_API_URL=https://api.devpocket.app
   DEVPOCKET_WS_URL=wss://api.devpocket.app
   
   # Optional (for server-side usage)
   DEVPOCKET_API_KEY=your-server-api-key
   
   # Monitoring (optional)
   SENTRY_DSN=your-sentry-dsn
   LOG_LEVEL=warn
   ```

2. **Security Considerations**
   - Use HTTPS/WSS in production
   - Validate SSL certificates
   - Implement proper token storage
   - Set up rate limiting
   - Enable request/response logging

3. **Performance Optimization**
   - Enable response caching
   - Implement connection pooling
   - Use CDN for static assets
   - Monitor API response times
   - Set up proper retry logic

4. **Monitoring and Alerting**
   - Set up health checks
   - Monitor error rates
   - Track API response times
   - Alert on authentication failures
   - Monitor WebSocket connection stability

This comprehensive developer integration guide provides everything needed to successfully integrate with the DevPocket API across different platforms and use cases.