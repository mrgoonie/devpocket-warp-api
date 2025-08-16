# DevPocket API SDK Generation Guide

## Overview

This guide provides comprehensive instructions for generating, customizing, and maintaining client SDKs for the DevPocket API using OpenAPI specifications. It includes templates, configuration files, and best practices for multiple programming languages.

## Prerequisites

### Required Tools

1. **OpenAPI Generator**
   ```bash
   npm install -g @openapitools/openapi-generator-cli
   # or
   brew install openapi-generator
   # or use Docker
   docker pull openapitools/openapi-generator-cli
   ```

2. **Swagger Codegen** (Alternative)
   ```bash
   npm install -g swagger-codegen
   ```

3. **Language-Specific Tools**
   - Node.js: npm/yarn, TypeScript
   - Python: pip, poetry, setuptools
   - Java: Maven/Gradle, JDK 11+
   - Go: Go 1.19+, go mod
   - C#: .NET 6+, NuGet

### Source Files

Ensure you have the latest OpenAPI specification:
- Main spec: `/docs/openapi.yaml`
- Custom templates: `/docs/sdk-templates/`
- Configuration files: `/docs/sdk-configs/`

## Supported Languages and SDKs

### JavaScript/TypeScript SDK

#### Generation Command
```bash
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g typescript-axios \
  -o sdk/typescript \
  -c docs/sdk-configs/typescript-config.json \
  --additional-properties=npmName=devpocket-api,npmVersion=1.0.0
```

#### Configuration File: `typescript-config.json`
```json
{
  "npmName": "devpocket-api",
  "npmVersion": "1.0.0",
  "npmRepository": "https://registry.npmjs.org/",
  "snapshot": false,
  "npmDescription": "Official DevPocket API client for TypeScript/JavaScript",
  "npmAuthor": "DevPocket Team",
  "npmKeywords": ["devpocket", "terminal", "ssh", "api", "typescript"],
  "licenseName": "MIT",
  "supportsES6": true,
  "typescriptThreePlus": true,
  "withInterfaces": true,
  "useSingleRequestParameter": true,
  "stringEnums": false,
  "enumNameSuffix": "",
  "modelPropertyNaming": "camelCase",
  "paramNaming": "camelCase",
  "enumPropertyNaming": "PascalCase"
}
```

#### Custom Template Modifications
Create custom templates in `docs/sdk-templates/typescript/`:

**api.mustache** (Enhanced with DevPocket features):
```typescript
{{>licenseInfo}}
import { Configuration } from './configuration';
import globalAxios, { AxiosPromise, AxiosInstance, AxiosRequestConfig } from 'axios';

{{#models}}
{{#model}}
{{>model}}
{{/model}}
{{/models}}

/**
 * DevPocket API Configuration with BYOK support
 */
export interface DevPocketConfig extends Configuration {
  /**
   * OpenRouter API key for BYOK AI features
   */
  openRouterApiKey?: string;
  
  /**
   * WebSocket URL for terminal connections
   */
  websocketUrl?: string;
  
  /**
   * Device identifier for multi-device sync
   */
  deviceId?: string;
}

/**
 * DevPocket API Client with enhanced features
 */
export class DevPocketAPI {
  private configuration: DevPocketConfig;
  private axios: AxiosInstance;

  constructor(config: DevPocketConfig) {
    this.configuration = config;
    this.axios = globalAxios.create({
      baseURL: config.basePath,
      headers: {
        'User-Agent': 'DevPocket-SDK/1.0.0',
        ...(config.accessToken && { 'Authorization': `Bearer ${config.accessToken}` }),
        ...(config.openRouterApiKey && { 'X-OpenRouter-Key': config.openRouterApiKey })
      }
    });
  }

  /**
   * Set JWT token for authentication
   */
  setAccessToken(token: string): void {
    this.configuration.accessToken = token;
    this.axios.defaults.headers['Authorization'] = `Bearer ${token}`;
  }

  /**
   * Set OpenRouter API key for BYOK AI features
   */
  setOpenRouterKey(key: string): void {
    this.configuration.openRouterApiKey = key;
    this.axios.defaults.headers['X-OpenRouter-Key'] = key;
  }

  /**
   * Create WebSocket connection for terminal
   */
  createWebSocketConnection(sessionId?: string): WebSocket {
    const wsUrl = this.configuration.websocketUrl || 
                  this.configuration.basePath?.replace('http', 'ws') + '/ws/terminal';
    
    const params = new URLSearchParams();
    if (this.configuration.accessToken) {
      params.append('token', this.configuration.accessToken);
    }
    if (this.configuration.deviceId) {
      params.append('device_id', this.configuration.deviceId);
    }
    if (sessionId) {
      params.append('session_id', sessionId);
    }

    return new WebSocket(`${wsUrl}?${params.toString()}`);
  }

{{#apiDocumentationUrl}}
  /**
   * {{apiDocumentationUrl}}
   */
{{/apiDocumentationUrl}}
{{#operations}}
{{#operation}}
  {{>operation}}
{{/operation}}
{{/operations}}
}
```

#### Usage Example
```typescript
import { DevPocketAPI, Configuration } from 'devpocket-api';

// Initialize client
const config: Configuration = {
  basePath: 'https://api.devpocket.app',
  accessToken: 'your-jwt-token',
  openRouterApiKey: 'sk-or-v1-your-key',
  deviceId: 'device-123'
};

const client = new DevPocketAPI(config);

// Authentication
const loginResponse = await client.authApi.login({
  email: 'user@example.com',
  password: 'password'
});

client.setAccessToken(loginResponse.data.access_token);

// SSH Profile Management
const profile = await client.sshApi.createSshProfile({
  name: 'Production Server',
  hostname: 'prod.example.com',
  username: 'deploy',
  port: 22,
  auth_type: 'key'
});

// AI Command Suggestions (BYOK)
const suggestion = await client.aiApi.suggestCommand({
  description: 'List all running Docker containers',
  context: 'docker'
});

// WebSocket Terminal Connection
const websocket = client.createWebSocketConnection();
websocket.onopen = () => {
  websocket.send(JSON.stringify({
    type: 'connect',
    data: {
      session_type: 'ssh',
      ssh_profile_id: profile.data.id,
      terminal_size: { rows: 24, cols: 80 }
    }
  }));
};
```

### Python SDK

#### Generation Command
```bash
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g python \
  -o sdk/python \
  -c docs/sdk-configs/python-config.json \
  --additional-properties=packageName=devpocket_api,projectName=devpocket-api
```

#### Configuration File: `python-config.json`
```json
{
  "packageName": "devpocket_api",
  "projectName": "devpocket-api",
  "packageVersion": "1.0.0",
  "packageDescription": "Official DevPocket API client for Python",
  "packageAuthor": "DevPocket Team",
  "packageAuthorEmail": "sdk@devpocket.app",
  "packageUrl": "https://github.com/devpocket/devpocket-python-sdk",
  "licenseName": "MIT",
  "generateSourceCodeOnly": false,
  "library": "asyncio",
  "pythonAtLeast3": true,
  "disallowAdditionalPropsIfNotPresent": false
}
```

#### Custom Template: `__init__.mustache`
```python
# coding: utf-8

"""
{{appName}}

{{appDescription}}

OpenAPI spec version: {{appVersion}}
{{#contact}}
Contact: {{contactEmail}}
{{/contact}}
Generated by: https://openapi-generator.tech
"""

from __future__ import absolute_import

import asyncio
import websockets
import json
from typing import Optional, Dict, Any
from urllib.parse import urlencode

{{#models}}
{{#model}}
# import models into sdk package
from {{packageName}}.models.{{classFilename}} import {{classname}}
{{/model}}
{{/models}}

{{#apis}}
{{#operations}}
# import apis into sdk package
from {{packageName}}.api.{{classFilename}} import {{classname}}
{{/operations}}
{{/apis}}

class DevPocketAPI:
    """
    DevPocket API Client with enhanced features for terminal management
    """
    
    def __init__(self, configuration=None):
        from {{packageName}}.configuration import Configuration
        from {{packageName}}.api_client import ApiClient
        
        self.configuration = configuration or Configuration()
        self.api_client = ApiClient(self.configuration)
        
        # Initialize API instances
{{#apis}}
{{#operations}}
        self.{{classVarName}} = {{classname}}(self.api_client)
{{/operations}}
{{/apis}}
    
    def set_access_token(self, token: str) -> None:
        """Set JWT access token for authentication"""
        self.configuration.access_token = token
        self.api_client.set_default_header('Authorization', f'Bearer {token}')
    
    def set_openrouter_key(self, key: str) -> None:
        """Set OpenRouter API key for BYOK AI features"""
        self.configuration.openrouter_key = key
        self.api_client.set_default_header('X-OpenRouter-Key', key)
    
    async def create_websocket_connection(
        self, 
        session_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> websockets.WebSocketServerProtocol:
        """Create WebSocket connection for terminal communication"""
        
        ws_url = self.configuration.host.replace('http', 'ws') + '/ws/terminal'
        
        params = {}
        if hasattr(self.configuration, 'access_token') and self.configuration.access_token:
            params['token'] = self.configuration.access_token
        if device_id:
            params['device_id'] = device_id
        if session_id:
            params['session_id'] = session_id
            
        if params:
            ws_url += '?' + urlencode(params)
        
        return await websockets.connect(ws_url)
    
    async def send_terminal_input(
        self, 
        websocket: websockets.WebSocketServerProtocol,
        session_id: str,
        input_data: str
    ) -> None:
        """Send input to terminal session"""
        message = {
            'type': 'input',
            'session_id': session_id,
            'data': input_data,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        await websocket.send(json.dumps(message))
    
    async def receive_terminal_output(
        self, 
        websocket: websockets.WebSocketServerProtocol
    ) -> Dict[str, Any]:
        """Receive output from terminal session"""
        message = await websocket.recv()
        return json.loads(message)

# For backward compatibility
{{#models}}
{{#model}}
from {{packageName}}.models.{{classFilename}} import {{classname}}
{{/model}}
{{/models}}
```

#### Usage Example
```python
import asyncio
from devpocket_api import DevPocketAPI, Configuration

async def main():
    # Initialize client
    config = Configuration()
    config.host = "https://api.devpocket.app"
    
    client = DevPocketAPI(config)
    
    # Authentication
    login_response = await client.auth_api.login_async({
        'email': 'user@example.com',
        'password': 'password'
    })
    
    client.set_access_token(login_response.access_token)
    client.set_openrouter_key('sk-or-v1-your-key')
    
    # Create SSH profile
    profile = await client.ssh_api.create_ssh_profile_async({
        'name': 'Production Server',
        'hostname': 'prod.example.com',
        'username': 'deploy',
        'port': 22,
        'auth_type': 'key'
    })
    
    # WebSocket terminal connection
    websocket = await client.create_websocket_connection(device_id='device-123')
    
    # Connect to SSH session
    await websocket.send(json.dumps({
        'type': 'connect',
        'data': {
            'session_type': 'ssh',
            'ssh_profile_id': profile.id,
            'terminal_size': {'rows': 24, 'cols': 80}
        }
    }))
    
    # Handle messages
    async for message in websocket:
        data = json.loads(message)
        if data['type'] == 'session_info':
            session_id = data['session_id']
            # Send command
            await client.send_terminal_input(websocket, session_id, 'ls -la\n')
        elif data['type'] == 'output':
            print(f"Terminal output: {data['data']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Java SDK

#### Generation Command
```bash
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g java \
  -o sdk/java \
  -c docs/sdk-configs/java-config.json \
  --additional-properties=groupId=app.devpocket,artifactId=devpocket-api,apiPackage=app.devpocket.api
```

#### Configuration File: `java-config.json`
```json
{
  "groupId": "app.devpocket",
  "artifactId": "devpocket-api",
  "apiPackage": "app.devpocket.api",
  "modelPackage": "app.devpocket.model",
  "invokerPackage": "app.devpocket.client",
  "packageName": "devpocket-api",
  "clientPackage": "app.devpocket.client",
  "packageVersion": "1.0.0",
  "packageDescription": "Official DevPocket API client for Java",
  "packageCompany": "DevPocket",
  "packageAuthor": "DevPocket Team",
  "packageEmail": "sdk@devpocket.app",
  "packageUrl": "https://github.com/devpocket/devpocket-java-sdk",
  "licenseName": "MIT",
  "licenseUrl": "https://opensource.org/licenses/MIT",
  "library": "okhttp-gson",
  "java8": false,
  "dateLibrary": "java8",
  "java11": true,
  "openApiNullable": false,
  "disallowAdditionalPropsIfNotPresent": false
}
```

#### Usage Example
```java
import app.devpocket.client.DevPocketAPI;
import app.devpocket.client.Configuration;
import app.devpocket.api.AuthApi;
import app.devpocket.api.SshApi;
import app.devpocket.api.AiApi;
import app.devpocket.model.*;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.nio.ByteBuffer;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;

public class DevPocketExample {
    public static void main(String[] args) {
        // Initialize client
        Configuration config = new Configuration();
        config.setHost("https://api.devpocket.app");
        
        DevPocketAPI client = new DevPocketAPI(config);
        
        try {
            // Authentication
            AuthApi authApi = new AuthApi(client.getApiClient());
            LoginRequest loginRequest = new LoginRequest()
                .email("user@example.com")
                .password("password");
            
            LoginResponse loginResponse = authApi.login(loginRequest);
            client.setAccessToken(loginResponse.getAccessToken());
            client.setOpenRouterKey("sk-or-v1-your-key");
            
            // Create SSH profile
            SshApi sshApi = new SshApi(client.getApiClient());
            SshProfileCreate profileRequest = new SshProfileCreate()
                .name("Production Server")
                .hostname("prod.example.com")
                .username("deploy")
                .port(22)
                .authType(SshProfileCreate.AuthTypeEnum.KEY);
            
            SshProfile profile = sshApi.createSshProfile(profileRequest);
            
            // WebSocket connection
            WebSocket.Builder wsBuilder = HttpClient.newHttpClient().newWebSocketBuilder();
            String wsUrl = config.getHost().replace("http", "ws") + "/ws/terminal"
                + "?token=" + loginResponse.getAccessToken()
                + "&device_id=device-123";
            
            CompletableFuture<WebSocket> wsFuture = wsBuilder.buildAsync(
                URI.create(wsUrl),
                new WebSocketHandler(profile.getId())
            );
            
            WebSocket websocket = wsFuture.get();
            
            // Keep connection alive
            Thread.sleep(30000);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    static class WebSocketHandler implements WebSocket.Listener {
        private final String profileId;
        
        public WebSocketHandler(String profileId) {
            this.profileId = profileId;
        }
        
        @Override
        public void onOpen(WebSocket webSocket) {
            System.out.println("WebSocket connected");
            
            // Connect to SSH session
            String connectMessage = String.format("""
                {
                  "type": "connect",
                  "data": {
                    "session_type": "ssh",
                    "ssh_profile_id": "%s",
                    "terminal_size": {"rows": 24, "cols": 80}
                  }
                }
                """, profileId);
            
            webSocket.sendText(connectMessage, true);
            WebSocket.Listener.super.onOpen(webSocket);
        }
        
        @Override
        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
            System.out.println("Received: " + data);
            return WebSocket.Listener.super.onText(webSocket, data, last);
        }
    }
}
```

### Go SDK

#### Generation Command
```bash
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g go \
  -o sdk/go \
  -c docs/sdk-configs/go-config.json \
  --additional-properties=packageName=devpocket,moduleName=github.com/devpocket/devpocket-go-sdk
```

#### Configuration File: `go-config.json`
```json
{
  "packageName": "devpocket",
  "moduleName": "github.com/devpocket/devpocket-go-sdk",
  "packageVersion": "1.0.0",
  "packageDescription": "Official DevPocket API client for Go",
  "packageCompany": "DevPocket",
  "packageAuthor": "DevPocket Team",
  "packageEmail": "sdk@devpocket.app",
  "packageUrl": "https://github.com/devpocket/devpocket-go-sdk",
  "licenseName": "MIT",
  "licenseUrl": "https://opensource.org/licenses/MIT",
  "generateInterfaces": true,
  "structPrefix": true,
  "enumClassPrefix": true
}
```

#### Usage Example
```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net/url"
    "time"

    "github.com/devpocket/devpocket-go-sdk"
    "github.com/gorilla/websocket"
)

func main() {
    // Initialize client
    config := devpocket.NewConfiguration()
    config.Host = "api.devpocket.app"
    config.Scheme = "https"
    
    client := devpocket.NewAPIClient(config)
    ctx := context.Background()
    
    // Authentication
    loginReq := devpocket.LoginRequest{
        Email:    "user@example.com",
        Password: "password",
    }
    
    loginResp, _, err := client.AuthApi.Login(ctx).LoginRequest(loginReq).Execute()
    if err != nil {
        log.Fatal(err)
    }
    
    // Set authentication
    ctx = context.WithValue(ctx, devpocket.ContextAccessToken, loginResp.AccessToken)
    
    // Create SSH profile
    profileReq := devpocket.SshProfileCreate{
        Name:     "Production Server",
        Hostname: "prod.example.com",
        Username: "deploy",
        Port:     22,
        AuthType: "key",
    }
    
    profile, _, err := client.SshApi.CreateSshProfile(ctx).SshProfileCreate(profileReq).Execute()
    if err != nil {
        log.Fatal(err)
    }
    
    // WebSocket connection
    u := url.URL{
        Scheme:   "ws",
        Host:     config.Host,
        Path:     "/ws/terminal",
        RawQuery: fmt.Sprintf("token=%s&device_id=device-123", loginResp.AccessToken),
    }
    
    conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
    if err != nil {
        log.Fatal(err)
    }
    defer conn.Close()
    
    // Connect to SSH session
    connectMsg := map[string]interface{}{
        "type": "connect",
        "data": map[string]interface{}{
            "session_type":    "ssh",
            "ssh_profile_id":  profile.Id,
            "terminal_size": map[string]int{
                "rows": 24,
                "cols": 80,
            },
        },
    }
    
    if err := conn.WriteJSON(connectMsg); err != nil {
        log.Fatal(err)
    }
    
    // Read messages
    for {
        _, message, err := conn.ReadMessage()
        if err != nil {
            log.Fatal(err)
        }
        
        var msg map[string]interface{}
        if err := json.Unmarshal(message, &msg); err != nil {
            log.Printf("Error parsing message: %v", err)
            continue
        }
        
        fmt.Printf("Received: %s\n", msg["type"])
        
        if msg["type"] == "session_info" {
            // Send test command
            inputMsg := map[string]interface{}{
                "type":       "input",
                "session_id": msg["session_id"],
                "data":       "ls -la\n",
                "timestamp":  time.Now().UTC().Format(time.RFC3339),
            }
            
            if err := conn.WriteJSON(inputMsg); err != nil {
                log.Printf("Error sending input: %v", err)
            }
        }
    }
}
```

## SDK Customization Templates

### Custom Error Handling

Create enhanced error handling across all SDKs:

#### TypeScript Error Template
```typescript
// File: docs/sdk-templates/typescript/error-handling.mustache
export class DevPocketAPIError extends Error {
  public readonly statusCode?: number;
  public readonly errorCode?: string;
  public readonly details?: any;
  public readonly retryable: boolean;

  constructor(
    message: string,
    statusCode?: number,
    errorCode?: string,
    details?: any,
    retryable: boolean = false
  ) {
    super(message);
    this.name = 'DevPocketAPIError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.details = details;
    this.retryable = retryable;
  }

  static fromResponse(response: any): DevPocketAPIError {
    const { status, data } = response;
    const errorCode = data?.error?.code || 'unknown_error';
    const message = data?.error?.message || 'An unknown error occurred';
    const details = data?.error?.details;
    
    // Determine if error is retryable
    const retryableErrors = ['rate_limited', 'server_error', 'timeout'];
    const retryable = retryableErrors.includes(errorCode) || status >= 500;
    
    return new DevPocketAPIError(message, status, errorCode, details, retryable);
  }
}

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffFactor: number;
}

export async function withRetry<T>(
  operation: () => Promise<T>,
  config: RetryConfig = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    backoffFactor: 2
  }
): Promise<T> {
  let lastError: DevPocketAPIError;
  
  for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error instanceof DevPocketAPIError 
        ? error 
        : new DevPocketAPIError(error.message);
      
      if (attempt === config.maxRetries || !lastError.retryable) {
        throw lastError;
      }
      
      const delay = Math.min(
        config.baseDelay * Math.pow(config.backoffFactor, attempt),
        config.maxDelay
      );
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
}
```

### WebSocket Manager Template

#### Universal WebSocket Manager
```typescript
// File: docs/sdk-templates/common/websocket-manager.mustache
export interface WebSocketMessage {
  type: string;
  session_id?: string;
  data: any;
  timestamp?: string;
}

export interface WebSocketConfig {
  url: string;
  token: string;
  deviceId?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
}

export class DevPocketWebSocketManager {
  private websocket?: WebSocket;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private pingTimer?: NodeJS.Timeout;
  private messageHandlers = new Map<string, Array<(message: WebSocketMessage) => void>>();

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      pingInterval: 30000,
      ...config
    };
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const params = new URLSearchParams({
        token: this.config.token,
        ...(this.config.deviceId && { device_id: this.config.deviceId })
      });
      
      const url = `${this.config.url}?${params.toString()}`;
      this.websocket = new WebSocket(url);

      this.websocket.onopen = () => {
        console.log('DevPocket WebSocket connected');
        this.reconnectAttempts = 0;
        this.startPingTimer();
        resolve();
      };

      this.websocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.websocket.onclose = (event) => {
        this.stopPingTimer();
        if (!event.wasClean && this.shouldReconnect()) {
          this.scheduleReconnect();
        }
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
    });
  }

  sendMessage(message: WebSocketMessage): void {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      if (!message.timestamp) {
        message.timestamp = new Date().toISOString();
      }
      this.websocket.send(JSON.stringify(message));
    } else {
      throw new Error('WebSocket not connected');
    }
  }

  onMessage(type: string, handler: (message: WebSocketMessage) => void): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(handler);
  }

  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type) || [];
    handlers.forEach(handler => handler(message));
  }

  private shouldReconnect(): boolean {
    return this.reconnectAttempts < (this.config.maxReconnectAttempts || 5);
  }

  private scheduleReconnect(): void {
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      this.config.reconnectInterval || 5000
    );
    
    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect().catch(() => {
        if (this.shouldReconnect()) {
          this.scheduleReconnect();
        }
      });
    }, delay);
  }

  private startPingTimer(): void {
    this.pingTimer = setInterval(() => {
      this.sendMessage({ type: 'ping', data: { timestamp: new Date().toISOString() } });
    }, this.config.pingInterval || 30000);
  }

  private stopPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = undefined;
    }
  }

  disconnect(): void {
    this.stopPingTimer();
    if (this.websocket) {
      this.websocket.close(1000, 'Client disconnect');
    }
  }
}
```

## Testing Templates

### SDK Testing Framework

#### Jest Configuration for TypeScript SDK
```javascript
// File: docs/sdk-templates/typescript/jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/test/**/*',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  testTimeout: 30000,
};
```

#### Test Utilities
```typescript
// File: docs/sdk-templates/typescript/test-utils.ts
import { DevPocketAPI } from '../src';
import { Server } from 'http';
import express from 'express';
import WebSocket from 'ws';

export class MockDevPocketServer {
  private app: express.Application;
  private server?: Server;
  private wsServer?: WebSocket.Server;
  private port: number;

  constructor(port: number = 3001) {
    this.port = port;
    this.app = express();
    this.app.use(express.json());
    this.setupRoutes();
  }

  private setupRoutes(): void {
    // Mock authentication
    this.app.post('/api/auth/login', (req, res) => {
      res.json({
        access_token: 'mock-jwt-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: 'user-123',
          email: req.body.email,
          subscription_tier: 'pro'
        }
      });
    });

    // Mock SSH profiles
    this.app.get('/api/ssh/profiles', (req, res) => {
      res.json({
        profiles: [
          {
            id: 'profile-123',
            name: 'Test Server',
            hostname: 'test.example.com',
            username: 'testuser',
            port: 22
          }
        ]
      });
    });

    // Mock AI endpoints
    this.app.post('/api/ai/suggest-command', (req, res) => {
      res.json({
        suggestion: {
          command: 'ls -la',
          description: 'List all files with details',
          confidence: 0.95
        }
      });
    });
  }

  async start(): Promise<void> {
    return new Promise((resolve) => {
      this.server = this.app.listen(this.port, () => {
        // Setup WebSocket server
        this.wsServer = new WebSocket.Server({ 
          port: this.port + 1,
          path: '/ws/terminal'
        });
        
        this.wsServer.on('connection', (ws) => {
          ws.on('message', (data) => {
            const message = JSON.parse(data.toString());
            
            // Echo back appropriate responses
            if (message.type === 'connect') {
              ws.send(JSON.stringify({
                type: 'session_info',
                session_id: 'mock-session-123',
                data: { status: 'connected' }
              }));
            }
            
            if (message.type === 'input') {
              ws.send(JSON.stringify({
                type: 'output',
                session_id: message.session_id,
                data: 'Mock terminal output\n'
              }));
            }
          });
        });
        
        resolve();
      });
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      this.wsServer?.close();
      this.server?.close(() => resolve());
    });
  }
}

export function createTestClient(): DevPocketAPI {
  return new DevPocketAPI({
    basePath: 'http://localhost:3001',
    websocketUrl: 'ws://localhost:3002/ws/terminal'
  });
}
```

#### Example Test Suite
```typescript
// File: docs/sdk-templates/typescript/api.test.ts
import { DevPocketAPI } from '../src';
import { MockDevPocketServer, createTestClient } from './test-utils';

describe('DevPocket API Client', () => {
  let server: MockDevPocketServer;
  let client: DevPocketAPI;

  beforeAll(async () => {
    server = new MockDevPocketServer();
    await server.start();
    client = createTestClient();
  });

  afterAll(async () => {
    await server.stop();
  });

  describe('Authentication', () => {
    it('should login successfully', async () => {
      const response = await client.authApi.login({
        email: 'test@example.com',
        password: 'password123'
      });

      expect(response.data.access_token).toBe('mock-jwt-token');
      expect(response.data.user.email).toBe('test@example.com');
    });

    it('should set access token', () => {
      client.setAccessToken('test-token');
      expect(client.configuration.accessToken).toBe('test-token');
    });
  });

  describe('SSH Management', () => {
    beforeEach(() => {
      client.setAccessToken('mock-jwt-token');
    });

    it('should list SSH profiles', async () => {
      const response = await client.sshApi.listSshProfiles();
      
      expect(response.data.profiles).toHaveLength(1);
      expect(response.data.profiles[0].name).toBe('Test Server');
    });
  });

  describe('WebSocket Terminal', () => {
    it('should create WebSocket connection', async () => {
      client.setAccessToken('mock-jwt-token');
      
      const websocket = client.createWebSocketConnection();
      
      await new Promise((resolve) => {
        websocket.onopen = resolve;
      });
      
      expect(websocket.readyState).toBe(WebSocket.OPEN);
      websocket.close();
    });

    it('should handle terminal messages', async () => {
      client.setAccessToken('mock-jwt-token');
      
      const websocket = client.createWebSocketConnection();
      const messages: any[] = [];
      
      websocket.onmessage = (event) => {
        messages.push(JSON.parse(event.data));
      };
      
      await new Promise((resolve) => {
        websocket.onopen = () => {
          websocket.send(JSON.stringify({
            type: 'connect',
            data: { session_type: 'ssh', ssh_profile_id: 'profile-123' }
          }));
          
          setTimeout(resolve, 100);
        };
      });
      
      expect(messages).toHaveLength(1);
      expect(messages[0].type).toBe('session_info');
      
      websocket.close();
    });
  });

  describe('AI Services', () => {
    beforeEach(() => {
      client.setAccessToken('mock-jwt-token');
      client.setOpenRouterKey('sk-or-v1-test-key');
    });

    it('should get command suggestions', async () => {
      const response = await client.aiApi.suggestCommand({
        description: 'list files',
        context: 'terminal'
      });
      
      expect(response.data.suggestion.command).toBe('ls -la');
      expect(response.data.suggestion.confidence).toBeGreaterThan(0.9);
    });
  });
});
```

## CI/CD Pipeline for SDK Generation

### GitHub Actions Workflow

```yaml
# File: .github/workflows/generate-sdks.yml
name: Generate and Publish SDKs

on:
  push:
    branches: [main]
    paths: ['docs/openapi.yaml']
  workflow_dispatch:

jobs:
  generate-sdks:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        sdk: [typescript, python, java, go, csharp]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Install OpenAPI Generator
        run: npm install -g @openapitools/openapi-generator-cli
        
      - name: Generate ${{ matrix.sdk }} SDK
        run: |
          mkdir -p sdk/${{ matrix.sdk }}
          openapi-generator-cli generate \
            -i docs/openapi.yaml \
            -g ${{ matrix.sdk }} \
            -o sdk/${{ matrix.sdk }} \
            -c docs/sdk-configs/${{ matrix.sdk }}-config.json
            
      - name: Run SDK tests
        run: |
          cd sdk/${{ matrix.sdk }}
          if [ -f package.json ]; then
            npm install && npm test
          elif [ -f requirements.txt ]; then
            pip install -r requirements.txt && python -m pytest
          elif [ -f pom.xml ]; then
            mvn test
          elif [ -f go.mod ]; then
            go test ./...
          fi
          
      - name: Upload SDK artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.sdk }}-sdk
          path: sdk/${{ matrix.sdk }}
          
  publish-sdks:
    needs: generate-sdks
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Download all SDK artifacts
        uses: actions/download-artifact@v3
        
      - name: Publish TypeScript SDK to NPM
        if: success()
        run: |
          cd typescript-sdk
          echo "//registry.npmjs.org/:_authToken=${{ secrets.NPM_TOKEN }}" > .npmrc
          npm publish
          
      - name: Publish Python SDK to PyPI
        if: success()
        run: |
          cd python-sdk
          pip install twine
          python setup.py sdist bdist_wheel
          twine upload dist/* -u __token__ -p ${{ secrets.PYPI_TOKEN }}
          
      - name: Publish Java SDK to Maven Central
        if: success()
        run: |
          cd java-sdk
          mvn deploy -s settings.xml
        env:
          MAVEN_USERNAME: ${{ secrets.MAVEN_USERNAME }}
          MAVEN_PASSWORD: ${{ secrets.MAVEN_PASSWORD }}
```

## Documentation Generation

### Auto-generate SDK Documentation

```bash
#!/bin/bash
# File: scripts/generate-sdk-docs.sh

set -e

SDKs=("typescript" "python" "java" "go" "csharp")
DOCS_DIR="docs/sdk-documentation"

echo "🚀 Generating SDK documentation..."

mkdir -p "$DOCS_DIR"

for sdk in "${SDKs[@]}"; do
    echo "📚 Generating $sdk documentation..."
    
    # Generate SDK
    openapi-generator-cli generate \
        -i docs/openapi.yaml \
        -g "$sdk" \
        -o "sdk/$sdk" \
        -c "docs/sdk-configs/$sdk-config.json"
    
    # Generate documentation based on SDK type
    case "$sdk" in
        "typescript")
            cd "sdk/$sdk"
            npm install
            npx typedoc src/index.ts --out "../../$DOCS_DIR/$sdk"
            cd ../..
            ;;
        "python")
            cd "sdk/$sdk"
            pip install -e .
            pip install sphinx sphinx-rtd-theme
            sphinx-quickstart -q --no-sep --project="DevPocket Python SDK" \
                --author="DevPocket Team" --release="1.0.0" \
                --language="en" --suffix=".rst" --master="index" \
                --extensions="sphinx.ext.autodoc,sphinx.ext.viewcode" .
            sphinx-build -b html . "../../$DOCS_DIR/$sdk"
            cd ../..
            ;;
        "java")
            cd "sdk/$sdk"
            mvn javadoc:javadoc
            cp -r target/site/apidocs/* "../../$DOCS_DIR/$sdk/"
            cd ../..
            ;;
        "go")
            cd "sdk/$sdk"
            godoc -http=:6060 &
            GODOC_PID=$!
            sleep 2
            wget -r -np -k -E --restrict-file-names=windows \
                http://localhost:6060/pkg/github.com/devpocket/devpocket-go-sdk/
            kill $GODOC_PID
            mv localhost:6060/pkg/github.com/devpocket/devpocket-go-sdk/* \
                "../../$DOCS_DIR/$sdk/"
            cd ../..
            ;;
    esac
    
    echo "✅ $sdk documentation generated"
done

echo "🎉 All SDK documentation generated successfully!"
echo "📖 Documentation available in: $DOCS_DIR"
```

This comprehensive SDK generation guide provides everything needed to create, customize, test, and maintain high-quality client SDKs for the DevPocket API across multiple programming languages. The templates include best practices for error handling, WebSocket management, testing, and CI/CD automation.