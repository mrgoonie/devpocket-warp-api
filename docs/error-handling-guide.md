# DevPocket API Error Handling and Troubleshooting Guide

## Overview

This guide provides comprehensive information about error handling, debugging, and troubleshooting common issues when integrating with the DevPocket API. It covers error response formats, common error scenarios, debugging techniques, and resolution strategies.

## Table of Contents

1. [Error Response Format](#error-response-format)
2. [HTTP Status Codes](#http-status-codes)
3. [Error Categories](#error-categories)
4. [Common Error Scenarios](#common-error-scenarios)
5. [WebSocket Error Handling](#websocket-error-handling)
6. [Debugging Techniques](#debugging-techniques)
7. [Rate Limiting](#rate-limiting)
8. [Troubleshooting Checklist](#troubleshooting-checklist)
9. [Code Examples](#code-examples)

## Error Response Format

All API errors follow a consistent JSON format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "type": "error_type",
    "details": {
      "field": "specific_field_error",
      "validation_errors": ["list", "of", "errors"]
    }
  }
}
```

### Error Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Specific error code for programmatic handling |
| `message` | string | Human-readable error description |
| `type` | string | Error category (e.g., "validation_error", "authentication_error") |
| `details` | object | Additional error information (optional) |

### Example Error Responses

**Validation Error:**
```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request validation failed",
    "type": "validation_error",
    "details": {
      "password": ["Password must be at least 8 characters long"],
      "email": ["Invalid email format"]
    }
  }
}
```

**Authentication Error:**
```json
{
  "error": {
    "code": "invalid_token",
    "message": "Access token is invalid or expired",
    "type": "authentication_error",
    "details": {
      "token_expired": true,
      "expires_at": "2023-01-01T12:00:00Z"
    }
  }
}
```

**Rate Limiting Error:**
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again later.",
    "type": "rate_limit_error",
    "details": {
      "limit": 100,
      "window": 3600,
      "retry_after": 1800
    }
  }
}
```

## HTTP Status Codes

### Success Codes (2xx)

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful GET, PUT, PATCH requests |
| 201 | Created | Successful POST requests (resource created) |
| 204 | No Content | Successful DELETE requests |

### Client Error Codes (4xx)

| Code | Description | Common Causes |
|------|-------------|---------------|
| 400 | Bad Request | Invalid request format, missing required fields |
| 401 | Unauthorized | Missing, invalid, or expired authentication |
| 403 | Forbidden | Insufficient permissions, subscription limitations |
| 404 | Not Found | Resource doesn't exist or user doesn't have access |
| 409 | Conflict | Resource already exists, concurrent modification |
| 422 | Unprocessable Entity | Valid format but validation failed |
| 423 | Locked | Account locked due to failed login attempts |
| 429 | Too Many Requests | Rate limit exceeded |

### Server Error Codes (5xx)

| Code | Description | Action |
|------|-------------|--------|
| 500 | Internal Server Error | Retry with exponential backoff, contact support |
| 502 | Bad Gateway | Temporary issue, retry after delay |
| 503 | Service Unavailable | Service maintenance, check status page |
| 504 | Gateway Timeout | Request timeout, retry with longer timeout |

## Error Categories

### 1. Authentication Errors

**Common Scenarios:**
- Missing Authorization header
- Invalid or malformed JWT token
- Expired access token
- Revoked or blacklisted token

**Error Codes:**
- `missing_authorization`
- `invalid_token`
- `token_expired`
- `token_revoked`
- `insufficient_permissions`

**Resolution:**
```typescript
class AuthErrorHandler {
  async handleAuthError(error: any): Promise<boolean> {
    switch (error.code) {
      case 'token_expired':
        // Attempt token refresh
        return await this.refreshToken();
      
      case 'invalid_token':
      case 'token_revoked':
        // Clear tokens and redirect to login
        this.clearTokens();
        this.redirectToLogin();
        return false;
      
      case 'insufficient_permissions':
        // Show upgrade prompt for subscription features
        this.showUpgradePrompt();
        return false;
      
      default:
        console.error('Unhandled auth error:', error);
        return false;
    }
  }

  private async refreshToken(): Promise<boolean> {
    try {
      const newToken = await this.authService.refreshToken();
      this.setAccessToken(newToken);
      return true;
    } catch (refreshError) {
      this.clearTokens();
      this.redirectToLogin();
      return false;
    }
  }
}
```

### 2. Validation Errors

**Common Scenarios:**
- Invalid input format
- Missing required fields
- Field length violations
- Pattern matching failures

**Error Codes:**
- `validation_failed`
- `missing_required_field`
- `invalid_format`
- `field_too_long`
- `field_too_short`
- `invalid_pattern`

**Resolution:**
```typescript
interface ValidationError {
  field: string;
  errors: string[];
}

class ValidationErrorHandler {
  handleValidationError(error: any): ValidationError[] {
    const validationErrors: ValidationError[] = [];
    
    if (error.details) {
      Object.entries(error.details).forEach(([field, errors]) => {
        if (Array.isArray(errors)) {
          validationErrors.push({ field, errors });
        }
      });
    }
    
    return validationErrors;
  }

  displayValidationErrors(errors: ValidationError[]): void {
    errors.forEach(({ field, errors: fieldErrors }) => {
      fieldErrors.forEach(errorMessage => {
        this.showFieldError(field, errorMessage);
      });
    });
  }

  private showFieldError(field: string, message: string): void {
    // Update UI to show field-specific error
    const fieldElement = document.querySelector(`[name="${field}"]`);
    if (fieldElement) {
      fieldElement.classList.add('error');
      this.addErrorMessage(fieldElement, message);
    }
  }
}
```

### 3. Resource Errors

**Common Scenarios:**
- Resource not found
- Access denied to resource
- Resource in invalid state
- Concurrent modification conflicts

**Error Codes:**
- `resource_not_found`
- `access_denied`
- `resource_locked`
- `conflict`
- `resource_limit_exceeded`

**Resolution:**
```typescript
class ResourceErrorHandler {
  async handleResourceError(error: any, context: any): Promise<void> {
    switch (error.code) {
      case 'resource_not_found':
        this.handleNotFound(context.resourceType, context.resourceId);
        break;
      
      case 'access_denied':
        this.handleAccessDenied(context.resourceType);
        break;
      
      case 'conflict':
        await this.handleConflict(context);
        break;
      
      case 'resource_limit_exceeded':
        this.handleLimitExceeded(error.details);
        break;
    }
  }

  private handleNotFound(resourceType: string, resourceId: string): void {
    console.warn(`${resourceType} ${resourceId} not found`);
    // Redirect to list view or show "not found" message
  }

  private handleAccessDenied(resourceType: string): void {
    console.warn(`Access denied to ${resourceType}`);
    // Show access denied message or redirect
  }

  private async handleConflict(context: any): Promise<void> {
    // Handle concurrent modification
    const choice = await this.showConflictDialog();
    if (choice === 'retry') {
      // Fetch latest data and retry
      await this.retryWithLatestData(context);
    }
  }

  private handleLimitExceeded(limits: any): void {
    // Show upgrade prompt or usage information
    this.showLimitExceededDialog(limits);
  }
}
```

### 4. Network Errors

**Common Scenarios:**
- Connection timeout
- Network connectivity issues
- DNS resolution failures
- SSL/TLS certificate errors

**Error Codes:**
- `network_error`
- `connection_timeout`
- `dns_error`
- `ssl_error`
- `connection_refused`

**Resolution:**
```typescript
class NetworkErrorHandler {
  private retryAttempts = 0;
  private maxRetries = 3;
  private baseDelay = 1000; // 1 second

  async handleNetworkError(error: any, originalRequest: Function): Promise<any> {
    if (this.retryAttempts >= this.maxRetries) {
      throw new Error('Max retry attempts exceeded');
    }

    const delay = this.calculateRetryDelay();
    await this.sleep(delay);
    
    this.retryAttempts++;
    
    try {
      return await originalRequest();
    } catch (retryError) {
      return this.handleNetworkError(retryError, originalRequest);
    }
  }

  private calculateRetryDelay(): number {
    // Exponential backoff with jitter
    const exponentialDelay = this.baseDelay * Math.pow(2, this.retryAttempts);
    const jitter = Math.random() * 1000; // 0-1 second jitter
    return exponentialDelay + jitter;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  resetRetryCount(): void {
    this.retryAttempts = 0;
  }
}
```

## Common Error Scenarios

### 1. SSH Connection Failures

**Symptoms:**
- SSH profiles fail to connect
- Timeout errors during connection
- Authentication failures

**Common Causes:**
```json
{
  "error": {
    "code": "ssh_connection_failed",
    "message": "Failed to establish SSH connection",
    "type": "connection_error",
    "details": {
      "reason": "authentication_failed",
      "host": "server.example.com",
      "port": 22,
      "username": "deploy"
    }
  }
}
```

**Troubleshooting Steps:**
1. Verify SSH credentials
2. Check network connectivity
3. Validate SSH server configuration
4. Test connection manually

```typescript
class SSHErrorHandler {
  async diagnoseSSHError(profileId: string): Promise<DiagnosisResult> {
    const diagnosis: DiagnosisResult = {
      issues: [],
      suggestions: []
    };

    try {
      // Test basic connectivity
      const connectivityTest = await this.testConnectivity(profileId);
      if (!connectivityTest.success) {
        diagnosis.issues.push('Network connectivity failed');
        diagnosis.suggestions.push('Check firewall and network settings');
      }

      // Test authentication
      const authTest = await this.testAuthentication(profileId);
      if (!authTest.success) {
        diagnosis.issues.push('Authentication failed');
        diagnosis.suggestions.push('Verify SSH credentials and key permissions');
      }

      // Test SSH server status
      const serverTest = await this.testSSHServer(profileId);
      if (!serverTest.success) {
        diagnosis.issues.push('SSH server not responding');
        diagnosis.suggestions.push('Contact server administrator');
      }

    } catch (error) {
      diagnosis.issues.push(`Diagnosis failed: ${error.message}`);
    }

    return diagnosis;
  }

  private async testConnectivity(profileId: string): Promise<TestResult> {
    // Implementation for connectivity test
    return { success: true, details: {} };
  }

  private async testAuthentication(profileId: string): Promise<TestResult> {
    // Implementation for auth test
    return { success: true, details: {} };
  }

  private async testSSHServer(profileId: string): Promise<TestResult> {
    // Implementation for server test
    return { success: true, details: {} };
  }
}

interface DiagnosisResult {
  issues: string[];
  suggestions: string[];
}

interface TestResult {
  success: boolean;
  details: any;
}
```

### 2. WebSocket Connection Issues

**Symptoms:**
- WebSocket connection drops
- Messages not being received
- Authentication failures

**Common Error Messages:**
```json
{
  "type": "error",
  "data": {
    "code": "websocket_auth_failed",
    "message": "WebSocket authentication failed",
    "details": {
      "reason": "invalid_token",
      "close_code": 1008
    }
  }
}
```

**Resolution:**
```typescript
class WebSocketErrorHandler {
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  handleWebSocketError(error: any): void {
    console.error('WebSocket error:', error);

    switch (error.code) {
      case 'websocket_auth_failed':
        this.handleAuthFailure();
        break;
      
      case 'connection_lost':
        this.handleConnectionLoss();
        break;
      
      case 'message_send_failed':
        this.handleSendFailure(error.data);
        break;
      
      default:
        this.handleGenericError(error);
    }
  }

  private handleAuthFailure(): void {
    console.warn('WebSocket authentication failed');
    // Refresh token and reconnect
    this.refreshTokenAndReconnect();
  }

  private handleConnectionLoss(): void {
    console.warn('WebSocket connection lost');
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.onMaxReconnectAttemptsReached();
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    
    setTimeout(() => {
      this.reconnectAttempts++;
      this.attemptReconnect();
    }, delay);
  }

  private async attemptReconnect(): Promise<void> {
    try {
      await this.websocket.connect();
      console.log('WebSocket reconnected successfully');
      this.reconnectAttempts = 0;
    } catch (error) {
      console.error('Reconnection failed:', error);
      this.scheduleReconnect();
    }
  }

  private async refreshTokenAndReconnect(): Promise<void> {
    try {
      await this.authService.refreshToken();
      await this.websocket.connect();
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.onAuthenticationFailed();
    }
  }

  private onMaxReconnectAttemptsReached(): void {
    // Show user notification about connection issues
    this.showConnectionIssueDialog();
  }

  private onAuthenticationFailed(): void {
    // Redirect to login
    this.redirectToLogin();
  }
}
```

### 3. AI Service Errors (BYOK)

**Symptoms:**
- API key validation failures
- AI request timeouts
- Rate limiting from OpenRouter

**Common Error Scenarios:**
```json
{
  "error": {
    "code": "openrouter_api_error",
    "message": "OpenRouter API request failed",
    "type": "external_api_error",
    "details": {
      "openrouter_error": "insufficient_quota",
      "openrouter_message": "Insufficient credits in account"
    }
  }
}
```

**Resolution:**
```typescript
class AIServiceErrorHandler {
  handleAIError(error: any): void {
    switch (error.code) {
      case 'invalid_api_key':
        this.handleInvalidAPIKey();
        break;
      
      case 'openrouter_rate_limit':
        this.handleRateLimit(error.details);
        break;
      
      case 'insufficient_quota':
        this.handleInsufficientQuota();
        break;
      
      case 'model_not_available':
        this.handleModelUnavailable(error.details);
        break;
      
      case 'ai_request_timeout':
        this.handleRequestTimeout();
        break;
      
      default:
        this.handleGenericAIError(error);
    }
  }

  private handleInvalidAPIKey(): void {
    // Show API key setup dialog
    this.showAPIKeyDialog({
      title: 'Invalid OpenRouter API Key',
      message: 'Please check your OpenRouter API key and try again.',
      action: 'update_key'
    });
  }

  private handleRateLimit(details: any): void {
    const waitTime = details.retry_after || 60;
    this.showRateLimitDialog({
      message: `Rate limit exceeded. Please wait ${waitTime} seconds.`,
      retryAfter: waitTime
    });
  }

  private handleInsufficientQuota(): void {
    this.showQuotaDialog({
      title: 'Insufficient Credits',
      message: 'Your OpenRouter account has insufficient credits.',
      actions: ['add_credits', 'switch_key']
    });
  }

  private handleModelUnavailable(details: any): void {
    const model = details.requested_model;
    const alternatives = details.available_models || [];
    
    this.showModelUnavailableDialog({
      unavailableModel: model,
      alternatives: alternatives
    });
  }

  private handleRequestTimeout(): void {
    this.showTimeoutDialog({
      message: 'AI request timed out. Please try again.',
      suggestion: 'Try using a faster model for better response times.'
    });
  }
}
```

## WebSocket Error Handling

### Connection Errors

WebSocket connections can fail for various reasons. Here's how to handle them:

```typescript
class WebSocketConnectionManager {
  private ws: WebSocket | null = null;
  private url: string;
  private protocols: string[];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private isIntentionallyClosed = false;

  constructor(url: string, protocols: string[] = []) {
    this.url = url;
    this.protocols = protocols;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url, this.protocols);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.isIntentionallyClosed = false;
          resolve();
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.handleClose(event);
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.handleError(error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        // Connection timeout
        setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleClose(event: CloseEvent): void {
    if (this.isIntentionallyClosed) {
      return;
    }

    const reason = this.getCloseReason(event.code);
    console.log(`WebSocket closed: ${reason}`);

    // Determine if we should reconnect
    if (this.shouldReconnect(event.code)) {
      this.scheduleReconnect();
    } else {
      this.onPermanentClose(event.code, reason);
    }
  }

  private getCloseReason(code: number): string {
    const reasons: { [key: number]: string } = {
      1000: 'Normal closure',
      1001: 'Going away',
      1002: 'Protocol error',
      1003: 'Unsupported data',
      1004: 'Reserved',
      1005: 'No status received',
      1006: 'Abnormal closure',
      1007: 'Invalid frame payload data',
      1008: 'Policy violation',
      1009: 'Message too big',
      1010: 'Mandatory extension',
      1011: 'Internal server error',
      1015: 'TLS handshake failure'
    };

    return reasons[code] || `Unknown error (${code})`;
  }

  private shouldReconnect(code: number): boolean {
    // Don't reconnect for certain error codes
    const noReconnectCodes = [1008, 1002, 1003]; // Policy violation, protocol error, unsupported data
    return !noReconnectCodes.includes(code) && this.reconnectAttempts < this.maxReconnectAttempts;
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.onMaxReconnectAttemptsReached();
        }
      });
    }, delay);
  }

  private handleError(error: Event): void {
    console.error('WebSocket error:', error);
    // Could emit error event for external handling
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data);
      
      if (message.type === 'error') {
        this.handleServerError(message.data);
      } else {
        // Handle normal messages
        this.onMessage(message);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleServerError(errorData: any): void {
    console.error('Server error:', errorData);
    
    switch (errorData.code) {
      case 'authentication_failed':
        this.onAuthenticationError();
        break;
      
      case 'session_expired':
        this.onSessionExpired();
        break;
      
      case 'rate_limited':
        this.onRateLimited(errorData.retry_after);
        break;
      
      default:
        this.onGenericServerError(errorData);
    }
  }

  private onPermanentClose(code: number, reason: string): void {
    console.error(`WebSocket permanently closed: ${reason}`);
    // Notify user about permanent connection loss
  }

  private onMaxReconnectAttemptsReached(): void {
    console.error('Max reconnection attempts reached');
    // Show user dialog about connection issues
  }

  private onAuthenticationError(): void {
    // Handle authentication error
    this.isIntentionallyClosed = true;
    this.ws?.close();
  }

  private onSessionExpired(): void {
    // Handle session expiration
    // Might try to refresh token and reconnect
  }

  private onRateLimited(retryAfter: number): void {
    // Handle rate limiting
    setTimeout(() => {
      this.connect();
    }, retryAfter * 1000);
  }

  private onGenericServerError(errorData: any): void {
    // Handle other server errors
    console.error('Generic server error:', errorData);
  }

  private onMessage(message: any): void {
    // Override in subclass or set callback
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  close(): void {
    this.isIntentionallyClosed = true;
    this.ws?.close();
  }
}
```

## Debugging Techniques

### 1. Request/Response Logging

```typescript
class APILogger {
  private isEnabled: boolean;
  private logLevel: 'debug' | 'info' | 'warn' | 'error';

  constructor(enabled = false, level: 'debug' | 'info' | 'warn' | 'error' = 'debug') {
    this.isEnabled = enabled;
    this.logLevel = level;
  }

  logRequest(method: string, url: string, headers: any, body?: any): void {
    if (!this.isEnabled) return;

    console.group(`🔄 API Request: ${method} ${url}`);
    console.log('Headers:', this.sanitizeHeaders(headers));
    if (body) {
      console.log('Body:', this.sanitizeBody(body));
    }
    console.log('Timestamp:', new Date().toISOString());
    console.groupEnd();
  }

  logResponse(method: string, url: string, status: number, headers: any, body?: any, duration?: number): void {
    if (!this.isEnabled) return;

    const emoji = status >= 200 && status < 300 ? '✅' : '❌';
    
    console.group(`${emoji} API Response: ${method} ${url} (${status})`);
    console.log('Status:', status);
    console.log('Headers:', headers);
    if (body) {
      console.log('Body:', body);
    }
    if (duration) {
      console.log('Duration:', `${duration}ms`);
    }
    console.log('Timestamp:', new Date().toISOString());
    console.groupEnd();
  }

  logError(method: string, url: string, error: any): void {
    if (!this.isEnabled) return;

    console.group(`🚨 API Error: ${method} ${url}`);
    console.error('Error:', error);
    console.log('Timestamp:', new Date().toISOString());
    console.groupEnd();
  }

  private sanitizeHeaders(headers: any): any {
    const sanitized = { ...headers };
    
    // Remove sensitive headers
    if (sanitized.Authorization) {
      sanitized.Authorization = sanitized.Authorization.replace(/Bearer .+/, 'Bearer ***');
    }
    
    return sanitized;
  }

  private sanitizeBody(body: any): any {
    if (typeof body !== 'object') return body;

    const sanitized = { ...body };
    
    // Remove sensitive fields
    const sensitiveFields = ['password', 'api_key', 'token', 'secret'];
    sensitiveFields.forEach(field => {
      if (sanitized[field]) {
        sanitized[field] = '***';
      }
    });
    
    return sanitized;
  }
}

// Usage with HTTP client
class DevPocketClient {
  private logger = new APILogger(process.env.NODE_ENV === 'development');

  async makeRequest(method: string, url: string, options: any = {}): Promise<any> {
    const startTime = Date.now();
    
    this.logger.logRequest(method, url, options.headers, options.body);

    try {
      const response = await fetch(url, {
        method,
        ...options
      });

      const duration = Date.now() - startTime;
      const responseBody = await response.json();
      
      this.logger.logResponse(method, url, response.status, response.headers, responseBody, duration);

      if (!response.ok) {
        throw new APIError(responseBody.error || 'Request failed', response.status);
      }

      return responseBody;
    } catch (error) {
      this.logger.logError(method, url, error);
      throw error;
    }
  }
}
```

### 2. Performance Monitoring

```typescript
class PerformanceMonitor {
  private metrics: Map<string, PerformanceMetric[]> = new Map();

  startTimer(operation: string): PerformanceTimer {
    const startTime = performance.now();
    
    return {
      operation,
      startTime,
      end: () => {
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        this.recordMetric(operation, duration);
        return duration;
      }
    };
  }

  recordMetric(operation: string, duration: number): void {
    if (!this.metrics.has(operation)) {
      this.metrics.set(operation, []);
    }

    this.metrics.get(operation)!.push({
      operation,
      duration,
      timestamp: Date.now()
    });

    // Keep only last 100 metrics per operation
    const metrics = this.metrics.get(operation)!;
    if (metrics.length > 100) {
      metrics.splice(0, metrics.length - 100);
    }
  }

  getMetrics(operation?: string): PerformanceMetric[] {
    if (operation) {
      return this.metrics.get(operation) || [];
    }

    // Return all metrics
    const allMetrics: PerformanceMetric[] = [];
    this.metrics.forEach(metrics => {
      allMetrics.push(...metrics);
    });
    
    return allMetrics.sort((a, b) => b.timestamp - a.timestamp);
  }

  getStats(operation: string): PerformanceStats | null {
    const metrics = this.metrics.get(operation);
    if (!metrics || metrics.length === 0) return null;

    const durations = metrics.map(m => m.duration);
    const sum = durations.reduce((a, b) => a + b, 0);
    
    return {
      operation,
      count: metrics.length,
      average: sum / metrics.length,
      min: Math.min(...durations),
      max: Math.max(...durations),
      latest: metrics[metrics.length - 1]?.duration || 0
    };
  }

  clearMetrics(operation?: string): void {
    if (operation) {
      this.metrics.delete(operation);
    } else {
      this.metrics.clear();
    }
  }
}

interface PerformanceTimer {
  operation: string;
  startTime: number;
  end(): number;
}

interface PerformanceMetric {
  operation: string;
  duration: number;
  timestamp: number;
}

interface PerformanceStats {
  operation: string;
  count: number;
  average: number;
  min: number;
  max: number;
  latest: number;
}

// Usage
const monitor = new PerformanceMonitor();

async function apiCall() {
  const timer = monitor.startTimer('api_call');
  
  try {
    const result = await fetch('/api/endpoint');
    return result;
  } finally {
    const duration = timer.end();
    console.log(`API call took ${duration.toFixed(2)}ms`);
  }
}

// Get performance stats
const stats = monitor.getStats('api_call');
console.log('API call performance:', stats);
```

### 3. Network Connectivity Testing

```typescript
class ConnectivityTester {
  private testEndpoints = [
    'https://api.devpocket.app/health',
    'https://httpbin.org/get',
    'https://www.google.com/favicon.ico'
  ];

  async testConnectivity(): Promise<ConnectivityResult> {
    const results: ConnectivityTestResult[] = [];

    for (const endpoint of this.testEndpoints) {
      const result = await this.testEndpoint(endpoint);
      results.push(result);
    }

    const successfulTests = results.filter(r => r.success).length;
    const hasConnectivity = successfulTests > 0;

    return {
      hasConnectivity,
      results,
      summary: {
        total: results.length,
        successful: successfulTests,
        failed: results.length - successfulTests
      }
    };
  }

  private async testEndpoint(url: string): Promise<ConnectivityTestResult> {
    const startTime = Date.now();
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(url, {
        method: 'GET',
        signal: controller.signal,
        mode: 'no-cors' // Avoid CORS issues for testing
      });

      clearTimeout(timeoutId);
      
      return {
        url,
        success: true,
        duration: Date.now() - startTime,
        status: response.status
      };
    } catch (error) {
      return {
        url,
        success: false,
        duration: Date.now() - startTime,
        error: error.message
      };
    }
  }

  async testWebSocketConnectivity(): Promise<WebSocketTestResult> {
    const wsUrl = 'wss://api.devpocket.app/ws/terminal';
    
    return new Promise((resolve) => {
      const startTime = Date.now();
      const timeout = setTimeout(() => {
        resolve({
          success: false,
          duration: 5000,
          error: 'Connection timeout'
        });
      }, 5000);

      try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          clearTimeout(timeout);
          ws.close();
          resolve({
            success: true,
            duration: Date.now() - startTime
          });
        };

        ws.onerror = (error) => {
          clearTimeout(timeout);
          resolve({
            success: false,
            duration: Date.now() - startTime,
            error: 'WebSocket connection failed'
          });
        };
      } catch (error) {
        clearTimeout(timeout);
        resolve({
          success: false,
          duration: Date.now() - startTime,
          error: error.message
        });
      }
    });
  }
}

interface ConnectivityResult {
  hasConnectivity: boolean;
  results: ConnectivityTestResult[];
  summary: {
    total: number;
    successful: number;
    failed: number;
  };
}

interface ConnectivityTestResult {
  url: string;
  success: boolean;
  duration: number;
  status?: number;
  error?: string;
}

interface WebSocketTestResult {
  success: boolean;
  duration: number;
  error?: string;
}
```

## Rate Limiting

### Understanding Rate Limits

DevPocket implements rate limiting at multiple levels:

1. **User-based limits** (per subscription tier)
2. **IP-based limits** (security protection)
3. **Endpoint-specific limits** (resource protection)

### Rate Limit Headers

All API responses include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1672531200
X-RateLimit-Retry-After: 60
```

### Handling Rate Limits

```typescript
class RateLimitHandler {
  private queues: Map<string, RequestQueue> = new Map();

  async handleRateLimit(error: any, request: () => Promise<any>): Promise<any> {
    if (error.code !== 'rate_limit_exceeded') {
      throw error;
    }

    const retryAfter = error.details?.retry_after || 60;
    const endpoint = this.getEndpointKey(error);

    // Queue the request
    return this.queueRequest(endpoint, request, retryAfter);
  }

  private async queueRequest(endpoint: string, request: () => Promise<any>, retryAfter: number): Promise<any> {
    if (!this.queues.has(endpoint)) {
      this.queues.set(endpoint, new RequestQueue());
    }

    const queue = this.queues.get(endpoint)!;
    return queue.enqueue(request, retryAfter);
  }

  private getEndpointKey(error: any): string {
    // Extract endpoint identifier from error or context
    return error.details?.endpoint || 'default';
  }
}

class RequestQueue {
  private queue: QueuedRequest[] = [];
  private processing = false;
  private nextProcessTime = 0;

  async enqueue(request: () => Promise<any>, retryAfter: number): Promise<any> {
    return new Promise((resolve, reject) => {
      this.queue.push({
        request,
        resolve,
        reject,
        retryAfter: retryAfter * 1000 // Convert to milliseconds
      });

      this.processQueue();
    });
  }

  private async processQueue(): Promise<void> {
    if (this.processing || this.queue.length === 0) {
      return;
    }

    this.processing = true;

    while (this.queue.length > 0) {
      const now = Date.now();
      
      if (now < this.nextProcessTime) {
        // Wait until we can process the next request
        await this.sleep(this.nextProcessTime - now);
      }

      const queuedRequest = this.queue.shift()!;
      
      try {
        const result = await queuedRequest.request();
        queuedRequest.resolve(result);
        
        // Set next process time based on rate limit
        this.nextProcessTime = Date.now() + queuedRequest.retryAfter;
      } catch (error) {
        queuedRequest.reject(error);
      }
    }

    this.processing = false;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

interface QueuedRequest {
  request: () => Promise<any>;
  resolve: (value: any) => void;
  reject: (error: any) => void;
  retryAfter: number;
}
```

## Troubleshooting Checklist

### Basic Connectivity

- [ ] Can you reach the API endpoint? (`curl https://api.devpocket.app/health`)
- [ ] Are you using the correct API URL?
- [ ] Is your internet connection stable?
- [ ] Are there any firewall restrictions?

### Authentication Issues

- [ ] Is your access token valid and not expired?
- [ ] Are you including the `Authorization` header correctly?
- [ ] Is the token format correct (`Bearer <token>`)?
- [ ] Have you tried refreshing the token?

### Request Format

- [ ] Is the Content-Type header set to `application/json`?
- [ ] Is the request body valid JSON?
- [ ] Are all required fields included?
- [ ] Are field values in the correct format?

### WebSocket Connections

- [ ] Are you using the correct WebSocket URL?
- [ ] Is the authentication token included in query parameters?
- [ ] Are you handling connection drops and reconnection?
- [ ] Is the message format correct?

### BYOK/AI Services

- [ ] Is your OpenRouter API key valid?
- [ ] Do you have sufficient credits in your OpenRouter account?
- [ ] Are you within the rate limits?
- [ ] Is the requested AI model available?

### Performance Issues

- [ ] Are you implementing proper retry logic?
- [ ] Are you caching responses where appropriate?
- [ ] Are you using batch operations for multiple requests?
- [ ] Are you monitoring API response times?

## Code Examples

### Complete Error Handler

```typescript
class ComprehensiveErrorHandler {
  private logger: APILogger;
  private monitor: PerformanceMonitor;
  private rateLimitHandler: RateLimitHandler;

  constructor() {
    this.logger = new APILogger(true);
    this.monitor = new PerformanceMonitor();
    this.rateLimitHandler = new RateLimitHandler();
  }

  async handleError(error: any, context: any): Promise<any> {
    // Log the error
    this.logger.logError(context.method, context.url, error);

    // Determine error type and handle accordingly
    switch (error.type) {
      case 'authentication_error':
        return this.handleAuthError(error, context);
      
      case 'validation_error':
        return this.handleValidationError(error, context);
      
      case 'rate_limit_error':
        return this.rateLimitHandler.handleRateLimit(error, context.originalRequest);
      
      case 'network_error':
        return this.handleNetworkError(error, context);
      
      case 'external_api_error':
        return this.handleExternalAPIError(error, context);
      
      default:
        return this.handleGenericError(error, context);
    }
  }

  private async handleAuthError(error: any, context: any): Promise<any> {
    switch (error.code) {
      case 'token_expired':
        // Try to refresh token
        try {
          await this.refreshToken();
          return context.originalRequest();
        } catch (refreshError) {
          this.redirectToLogin();
          throw new Error('Authentication required');
        }
      
      case 'invalid_token':
        this.clearAuthData();
        this.redirectToLogin();
        throw new Error('Invalid authentication');
      
      case 'insufficient_permissions':
        this.showUpgradeDialog();
        throw new Error('Insufficient permissions');
      
      default:
        throw error;
    }
  }

  private handleValidationError(error: any, context: any): any {
    // Format validation errors for UI display
    const formattedErrors = this.formatValidationErrors(error.details);
    
    // Show validation errors in UI
    this.displayValidationErrors(formattedErrors);
    
    throw new ValidationError('Validation failed', formattedErrors);
  }

  private async handleNetworkError(error: any, context: any): Promise<any> {
    const maxRetries = 3;
    const baseDelay = 1000;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      if (attempt > 1) {
        const delay = baseDelay * Math.pow(2, attempt - 1);
        await this.sleep(delay);
      }

      try {
        return await context.originalRequest();
      } catch (retryError) {
        if (attempt === maxRetries) {
          throw new Error('Network error: Max retries exceeded');
        }
      }
    }
  }

  private handleExternalAPIError(error: any, context: any): any {
    // Handle errors from external APIs (e.g., OpenRouter)
    switch (error.details?.provider) {
      case 'openrouter':
        return this.handleOpenRouterError(error, context);
      
      default:
        throw error;
    }
  }

  private handleOpenRouterError(error: any, context: any): any {
    switch (error.details?.openrouter_error) {
      case 'insufficient_quota':
        this.showQuotaExhaustedDialog();
        break;
      
      case 'model_not_found':
        this.showModelUnavailableDialog(error.details.model);
        break;
      
      case 'rate_limited':
        // Handle OpenRouter rate limiting
        const retryAfter = error.details.retry_after || 60;
        this.showRateLimitDialog(retryAfter);
        break;
    }
    
    throw error;
  }

  private handleGenericError(error: any, context: any): any {
    console.error('Unhandled error:', error);
    
    // Show generic error message to user
    this.showGenericErrorDialog();
    
    throw error;
  }

  // Utility methods
  private async refreshToken(): Promise<void> {
    // Implementation for token refresh
  }

  private clearAuthData(): void {
    // Clear stored authentication data
  }

  private redirectToLogin(): void {
    // Redirect user to login page
  }

  private showUpgradeDialog(): void {
    // Show subscription upgrade dialog
  }

  private displayValidationErrors(errors: any[]): void {
    // Display validation errors in UI
  }

  private formatValidationErrors(details: any): any[] {
    // Format validation errors for display
    return Object.entries(details).map(([field, errors]) => ({
      field,
      errors: Array.isArray(errors) ? errors : [errors]
    }));
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private showQuotaExhaustedDialog(): void {
    // Show dialog about insufficient OpenRouter credits
  }

  private showModelUnavailableDialog(model: string): void {
    // Show dialog about unavailable AI model
  }

  private showRateLimitDialog(retryAfter: number): void {
    // Show dialog about rate limiting
  }

  private showGenericErrorDialog(): void {
    // Show generic error dialog
  }
}

class ValidationError extends Error {
  constructor(message: string, public errors: any[]) {
    super(message);
    this.name = 'ValidationError';
  }
}
```

This comprehensive error handling and troubleshooting guide provides developers with the tools and knowledge needed to effectively handle errors, debug issues, and build robust applications with the DevPocket API.