# DevPocket API Authentication Guide

## Overview

The DevPocket API uses JSON Web Tokens (JWT) for authentication and authorization. This guide covers the complete authentication flow, token management, security best practices, and the BYOK (Bring Your Own Key) model for AI services.

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [JWT Token Management](#jwt-token-management)
3. [API Endpoints](#api-endpoints)
4. [BYOK Model](#byok-model)
5. [Security Best Practices](#security-best-practices)
6. [Code Examples](#code-examples)
7. [Troubleshooting](#troubleshooting)

## Authentication Flow

### 1. User Registration

Create a new user account with email, username, and password.

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123!",
  "display_name": "John Doe",
  "device_id": "device-abc123",
  "device_type": "ios"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "johndoe",
    "display_name": "John Doe",
    "subscription_tier": "free",
    "is_active": true,
    "is_verified": false,
    "created_at": "2023-01-01T12:00:00Z"
  }
}
```

### 2. User Login

Authenticate with existing credentials.

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePass123!&grant_type=password
```

**Alternative JSON format:**
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "johndoe",
    "subscription_tier": "pro",
    "is_active": true,
    "is_verified": true,
    "created_at": "2023-01-01T12:00:00Z"
  }
}
```

### 3. Token Refresh

Obtain a new access token using the refresh token.

```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 4. Logout

Invalidate the current access token.

```http
POST /api/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "message": "Logout successful"
}
```

## JWT Token Management

### Enhanced Token Structure

DevPocket JWT tokens have been enhanced to properly handle UUID and datetime serialization. The tokens contain the following claims:

```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "username": "johndoe",
  "subscription_tier": "pro",
  "iat": 1672531200,
  "exp": 1672534800,
  "type": "access",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "device_id": "device-abc123"
}
```

### Token Serialization Improvements

Recent infrastructure improvements include:
- **UUID Handling**: Proper serialization of UUID objects in JWT tokens
- **Datetime Serialization**: Enhanced handling of datetime objects for token expiration
- **Type Safety**: Improved type validation for token claims
- **Error Handling**: Better error messages for token validation failures

### Token Types

1. **Access Token**
   - Short-lived (1-24 hours)
   - Used for API authentication
   - Contains user identity and permissions

2. **Refresh Token**
   - Long-lived (7-30 days)
   - Used to obtain new access tokens
   - Stored securely on client

### Using Tokens

Include the access token in the Authorization header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Storage

**Web Applications:**
- Store access token in memory
- Store refresh token in httpOnly cookie or secure storage

**Mobile Applications:**
- Use secure keychain/keystore
- Encrypt tokens before storage

**Never store tokens in:**
- Local storage (XSS vulnerable)
- Plain text files
- URL parameters
- Console logs

## API Endpoints

### Password Management

#### Forgot Password

Request a password reset email.

```http
POST /api/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If the email exists in our system, you will receive a password reset link."
}
```

#### Reset Password

Reset password using token from email.

```http
POST /api/auth/reset-password
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "NewSecurePass123!"
}
```

#### Change Password

Change password with current password verification.

```http
POST /api/auth/change-password
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePass123!"
}
```

### User Information

#### Get Current User

Retrieve authenticated user information.

```http
GET /api/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "username": "johndoe",
  "display_name": "John Doe",
  "subscription_tier": "pro",
  "is_active": true,
  "is_verified": true,
  "created_at": "2023-01-01T12:00:00Z",
  "updated_at": "2023-01-01T12:00:00Z"
}
```

#### Account Status

Check account lock status and failed login attempts.

```http
GET /api/auth/account-status
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "is_locked": false,
  "locked_until": null,
  "failed_attempts": 0
}
```

## BYOK Model

### Overview

DevPocket uses a "Bring Your Own Key" (BYOK) model for AI services, meaning users provide their own OpenRouter API keys. This approach offers several benefits:

- **Cost Control**: Users pay OpenRouter directly for AI usage
- **Privacy**: API keys never stored, only validated
- **Model Choice**: Access to latest AI models on OpenRouter
- **High Margins**: 85-98% gross margins for DevPocket

### OpenRouter Integration

#### API Key Validation

Validate an OpenRouter API key before use.

```http
POST /api/ai/validate-key
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "api_key": "sk-or-v1-abc123..."
}
```

**Response:**
```json
{
  "valid": true,
  "models_available": 15,
  "account_info": {
    "credit_balance": 25.50,
    "rate_limit": {
      "requests_per_minute": 60
    }
  },
  "error": null
}
```

#### Getting OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Create an account or sign in
3. Navigate to API Keys section
4. Generate a new API key
5. Copy the key (starts with `sk-or-v1-`)

#### Supported Models

DevPocket supports all OpenRouter models, including:

- **Google Gemini 2.5 Flash** (recommended for most tasks)
- **OpenAI GPT-4o** (advanced reasoning)
- **Anthropic Claude 3.5 Sonnet** (code analysis)
- **Meta Llama 3.1** (open source option)

### AI Service Usage

#### Command Suggestions

Get AI-powered command suggestions using your API key.

```http
POST /api/ai/suggest-command
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "api_key": "sk-or-v1-abc123...",
  "description": "List all files in the current directory with detailed information",
  "current_directory": "/home/user/projects",
  "shell_type": "bash",
  "os_type": "linux",
  "max_suggestions": 3,
  "include_explanations": true,
  "preferred_model": "google/gemini-2.5-flash"
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "command": "ls -la",
      "description": "Lists all files and directories with detailed information including hidden files",
      "confidence_score": 0.95,
      "safety_level": "safe",
      "tags": ["file-management", "listing"]
    },
    {
      "command": "ls -lah",
      "description": "Lists all files with human-readable file sizes",
      "confidence_score": 0.90,
      "safety_level": "safe",
      "tags": ["file-management", "listing"]
    }
  ],
  "model_used": "google/gemini-2.5-flash",
  "confidence_score": 0.92,
  "response_time_ms": 1250,
  "tokens_used": {
    "prompt_tokens": 45,
    "completion_tokens": 120,
    "total_tokens": 165
  }
}
```

#### Error Analysis

Analyze command errors with AI assistance.

```http
POST /api/ai/explain-error
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "api_key": "sk-or-v1-abc123...",
  "command": "npm install",
  "error_output": "npm ERR! code EACCES\nnpm ERR! syscall mkdir\nnpm ERR! path /usr/local/lib/node_modules",
  "exit_code": 1,
  "context": {
    "working_directory": "/home/user/project",
    "environment": {
      "NODE_ENV": "development"
    }
  }
}
```

**Response:**
```json
{
  "error_analysis": "This error occurs because npm is trying to install packages globally but doesn't have write permissions to the system directory.",
  "root_cause": "Permission denied - insufficient privileges for global package installation",
  "solutions": [
    {
      "solution": "Use sudo to run with elevated privileges",
      "command": "sudo npm install -g package-name",
      "risk_level": "low",
      "explanation": "Running with sudo gives npm the necessary permissions"
    },
    {
      "solution": "Use a Node version manager like nvm",
      "command": "nvm use node && npm install",
      "risk_level": "low",
      "explanation": "nvm manages Node installations in user directory"
    }
  ],
  "prevention_tips": [
    "Use a Node version manager like nvm",
    "Configure npm to use a different directory for global packages"
  ],
  "model_used": "google/gemini-2.5-flash",
  "confidence_score": 0.92
}
```

### BYOK Security

#### Key Handling

1. **No Storage**: API keys are never stored in DevPocket's database
2. **Validation Only**: Keys are only used for validation and immediate API calls
3. **Encrypted Transit**: All API key transmissions use HTTPS/WSS
4. **Memory Only**: Keys exist only in request memory and are discarded after use

#### Rate Limiting

- DevPocket applies its own rate limits (50-500 requests/minute based on tier)
- OpenRouter applies their own rate limits (varies by key)
- Failed requests due to rate limits are clearly indicated

#### Cost Management

- Users pay OpenRouter directly for AI usage
- Typical costs: $0.001-0.01 per request depending on model
- DevPocket provides usage estimates but not billing

## Security Best Practices

### Client-Side Security

1. **Token Storage**
   ```javascript
   // ✅ Good: Store in memory
   class AuthService {
     private accessToken: string | null = null;
     
     setToken(token: string) {
       this.accessToken = token;
     }
   }
   
   // ❌ Bad: Store in localStorage
   localStorage.setItem('token', token);
   ```

2. **Automatic Token Refresh**
   ```javascript
   class AuthService {
     async refreshTokenIfNeeded() {
       const token = this.accessToken;
       if (!token) return false;
       
       const payload = JSON.parse(atob(token.split('.')[1]));
       const now = Date.now() / 1000;
       
       // Refresh if token expires in less than 5 minutes
       if (payload.exp - now < 300) {
         return await this.refreshToken();
       }
       return true;
     }
   }
   ```

3. **Secure HTTP Requests**
   ```javascript
   const apiClient = axios.create({
     baseURL: 'https://api.devpocket.app',
     timeout: 10000,
     headers: {
       'Content-Type': 'application/json'
     }
   });

   // Add auth header interceptor
   apiClient.interceptors.request.use((config) => {
     const token = authService.getToken();
     if (token) {
       config.headers.Authorization = `Bearer ${token}`;
     }
     return config;
   });
   ```

### Server-Side Security

1. **Rate Limiting**: 5 login attempts per 15 minutes per IP/username
2. **Account Locking**: Temporary lock after 5 failed attempts
3. **Password Requirements**: 8+ characters, mixed case, numbers, symbols
4. **Token Blacklisting**: Logout immediately blacklists tokens
5. **HTTPS Only**: All authentication endpoints require HTTPS
6. **Enhanced JWT Security**: Improved token serialization with proper UUID and datetime handling
7. **Database Session Management**: Robust transaction handling and connection lifecycle management

### Password Security

#### Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

#### Validation Example

```javascript
function validatePassword(password) {
  const requirements = [
    { regex: /.{8,}/, message: "At least 8 characters long" },
    { regex: /[A-Z]/, message: "At least one uppercase letter" },
    { regex: /[a-z]/, message: "At least one lowercase letter" },
    { regex: /\d/, message: "At least one number" },
    { regex: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\?]/, message: "At least one special character" }
  ];

  const errors = requirements
    .filter(req => !req.regex.test(password))
    .map(req => req.message);

  return {
    isValid: errors.length === 0,
    errors
  };
}
```

## Code Examples

### JavaScript/TypeScript

#### Complete Authentication Service

```typescript
interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface User {
  id: string;
  email: string;
  username: string;
  subscription_tier: string;
}

class DevPocketAuth {
  private baseURL: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(baseURL: string = 'https://api.devpocket.app') {
    this.baseURL = baseURL;
  }

  async register(userData: {
    email: string;
    username: string;
    password: string;
    display_name?: string;
    device_id?: string;
    device_type?: 'ios' | 'android' | 'web';
  }): Promise<{tokens: AuthTokens; user: User}> {
    const response = await fetch(`${this.baseURL}/api/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    const data = await response.json();
    this.setTokens(data.access_token, data.refresh_token);
    
    return {
      tokens: {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        expires_in: data.expires_in,
      },
      user: data.user,
    };
  }

  async login(username: string, password: string): Promise<{tokens: AuthTokens; user: User}> {
    const response = await fetch(`${this.baseURL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }

    const data = await response.json();
    this.setTokens(data.access_token, data.refresh_token);
    
    return {
      tokens: {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        expires_in: data.expires_in,
      },
      user: data.user,
    };
  }

  async logout(): Promise<void> {
    if (this.accessToken) {
      try {
        await fetch(`${this.baseURL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
          },
        });
      } catch (error) {
        console.warn('Logout request failed:', error);
      }
    }
    
    this.clearTokens();
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.authenticatedRequest('/api/auth/me');
    return response.json();
  }

  async refreshTokens(): Promise<boolean> {
    // Prevent multiple simultaneous refresh attempts
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this.performTokenRefresh();
    const result = await this.refreshPromise;
    this.refreshPromise = null;
    
    return result;
  }

  private async performTokenRefresh(): Promise<boolean> {
    if (!this.refreshToken) {
      return false;
    }

    try {
      const response = await fetch(`${this.baseURL}/api/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: this.refreshToken,
        }),
      });

      if (!response.ok) {
        this.clearTokens();
        return false;
      }

      const data = await response.json();
      this.accessToken = data.access_token;
      
      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.clearTokens();
      return false;
    }
  }

  async authenticatedRequest(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<Response> {
    // Check if token needs refresh
    if (this.shouldRefreshToken()) {
      const refreshed = await this.refreshTokens();
      if (!refreshed) {
        throw new Error('Authentication required');
      }
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${this.accessToken}`,
      },
    });

    // Handle 401 errors by attempting token refresh
    if (response.status === 401) {
      const refreshed = await this.refreshTokens();
      if (refreshed) {
        // Retry the request with new token
        return fetch(`${this.baseURL}${endpoint}`, {
          ...options,
          headers: {
            ...options.headers,
            'Authorization': `Bearer ${this.accessToken}`,
          },
        });
      } else {
        throw new Error('Authentication required');
      }
    }

    return response;
  }

  private shouldRefreshToken(): boolean {
    if (!this.accessToken) return false;

    try {
      const payload = JSON.parse(atob(this.accessToken.split('.')[1]));
      const now = Date.now() / 1000;
      
      // Refresh if token expires in less than 5 minutes
      return payload.exp - now < 300;
    } catch {
      return true; // Invalid token, should refresh
    }
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
  }

  isAuthenticated(): boolean {
    return this.accessToken !== null;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }
}

// Usage example
const auth = new DevPocketAuth();

// Register new user
try {
  const {tokens, user} = await auth.register({
    email: 'user@example.com',
    username: 'johndoe',
    password: 'SecurePass123!',
    display_name: 'John Doe',
    device_type: 'web'
  });
  console.log('Registration successful:', user);
} catch (error) {
  console.error('Registration failed:', error.message);
}

// Login existing user
try {
  const {tokens, user} = await auth.login('user@example.com', 'SecurePass123!');
  console.log('Login successful:', user);
} catch (error) {
  console.error('Login failed:', error.message);
}

// Make authenticated requests
try {
  const response = await auth.authenticatedRequest('/api/sessions');
  const sessions = await response.json();
  console.log('User sessions:', sessions);
} catch (error) {
  console.error('Request failed:', error.message);
}
```

### React Hook Example

```typescript
import { useState, useEffect, useContext, createContext } from 'react';

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  register: (userData: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const auth = new DevPocketAuth();

  useEffect(() => {
    // Check for existing authentication on app start
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    if (auth.isAuthenticated()) {
      try {
        const userData = await auth.getCurrentUser();
        setUser(userData);
      } catch (error) {
        console.error('Auth check failed:', error);
        await auth.logout();
      }
    }
    setIsLoading(false);
  };

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const {user: userData} = await auth.login(username, password);
      setUser(userData);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterData) => {
    setIsLoading(true);
    try {
      const {user: newUser} = await auth.register(userData);
      setUser(newUser);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    await auth.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      login,
      register,
      logout,
      isAuthenticated: user !== null,
      isLoading,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### Flutter/Dart Example

```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AuthTokens {
  final String accessToken;
  final String refreshToken;
  final int expiresIn;

  AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
  });

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token'],
      refreshToken: json['refresh_token'],
      expiresIn: json['expires_in'],
    );
  }
}

class User {
  final String id;
  final String email;
  final String username;
  final String subscriptionTier;

  User({
    required this.id,
    required this.email,
    required this.username,
    required this.subscriptionTier,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      username: json['username'],
      subscriptionTier: json['subscription_tier'],
    );
  }
}

class DevPocketAuth {
  static const String _baseURL = 'https://api.devpocket.app';
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';

  String? _accessToken;
  String? _refreshToken;
  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    _accessToken = _prefs?.getString(_accessTokenKey);
    _refreshToken = _prefs?.getString(_refreshTokenKey);
  }

  Future<AuthResult> register({
    required String email,
    required String username,
    required String password,
    String? displayName,
    String? deviceId,
    String? deviceType,
  }) async {
    final response = await http.post(
      Uri.parse('$_baseURL/api/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'username': username,
        'password': password,
        if (displayName != null) 'display_name': displayName,
        if (deviceId != null) 'device_id': deviceId,
        if (deviceType != null) 'device_type': deviceType,
      }),
    );

    if (response.statusCode == 201) {
      final data = jsonDecode(response.body);
      await _setTokens(data['access_token'], data['refresh_token']);
      
      return AuthResult(
        tokens: AuthTokens.fromJson(data),
        user: User.fromJson(data['user']),
      );
    } else {
      final error = jsonDecode(response.body);
      throw AuthException(error['message'] ?? 'Registration failed');
    }
  }

  Future<AuthResult> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$_baseURL/api/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await _setTokens(data['access_token'], data['refresh_token']);
      
      return AuthResult(
        tokens: AuthTokens.fromJson(data),
        user: User.fromJson(data['user']),
      );
    } else {
      final error = jsonDecode(response.body);
      throw AuthException(error['message'] ?? 'Login failed');
    }
  }

  Future<void> logout() async {
    if (_accessToken != null) {
      try {
        await http.post(
          Uri.parse('$_baseURL/api/auth/logout'),
          headers: {'Authorization': 'Bearer $_accessToken'},
        );
      } catch (e) {
        print('Logout request failed: $e');
      }
    }
    
    await _clearTokens();
  }

  Future<User> getCurrentUser() async {
    final response = await _authenticatedRequest('/api/auth/me');
    return User.fromJson(jsonDecode(response.body));
  }

  Future<bool> refreshTokens() async {
    if (_refreshToken == null) return false;

    try {
      final response = await http.post(
        Uri.parse('$_baseURL/api/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': _refreshToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _accessToken = data['access_token'];
        await _prefs?.setString(_accessTokenKey, _accessToken!);
        return true;
      } else {
        await _clearTokens();
        return false;
      }
    } catch (e) {
      print('Token refresh failed: $e');
      await _clearTokens();
      return false;
    }
  }

  Future<http.Response> _authenticatedRequest(
    String endpoint, {
    String method = 'GET',
    Map<String, dynamic>? body,
  }) async {
    if (_shouldRefreshToken()) {
      final refreshed = await refreshTokens();
      if (!refreshed) {
        throw AuthException('Authentication required');
      }
    }

    final headers = {
      'Authorization': 'Bearer $_accessToken',
      'Content-Type': 'application/json',
    };

    http.Response response;
    final uri = Uri.parse('$_baseURL$endpoint');

    switch (method.toUpperCase()) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(
          uri,
          headers: headers,
          body: body != null ? jsonEncode(body) : null,
        );
        break;
      case 'PUT':
        response = await http.put(
          uri,
          headers: headers,
          body: body != null ? jsonEncode(body) : null,
        );
        break;
      case 'DELETE':
        response = await http.delete(uri, headers: headers);
        break;
      default:
        throw ArgumentError('Unsupported HTTP method: $method');
    }

    if (response.statusCode == 401) {
      final refreshed = await refreshTokens();
      if (refreshed) {
        // Retry request with new token
        headers['Authorization'] = 'Bearer $_accessToken';
        switch (method.toUpperCase()) {
          case 'GET':
            return http.get(uri, headers: headers);
          case 'POST':
            return http.post(
              uri,
              headers: headers,
              body: body != null ? jsonEncode(body) : null,
            );
          // ... other methods
        }
      } else {
        throw AuthException('Authentication required');
      }
    }

    return response;
  }

  bool _shouldRefreshToken() {
    if (_accessToken == null) return false;

    try {
      final parts = _accessToken!.split('.');
      final payload = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      );
      final exp = payload['exp'] as int;
      final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      
      // Refresh if token expires in less than 5 minutes
      return exp - now < 300;
    } catch (e) {
      return true; // Invalid token, should refresh
    }
  }

  Future<void> _setTokens(String accessToken, String refreshToken) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
    
    await _prefs?.setString(_accessTokenKey, accessToken);
    await _prefs?.setString(_refreshTokenKey, refreshToken);
  }

  Future<void> _clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
    
    await _prefs?.remove(_accessTokenKey);
    await _prefs?.remove(_refreshTokenKey);
  }

  bool get isAuthenticated => _accessToken != null;
  String? get accessToken => _accessToken;
}

class AuthResult {
  final AuthTokens tokens;
  final User user;

  AuthResult({required this.tokens, required this.user});
}

class AuthException implements Exception {
  final String message;
  AuthException(this.message);
  
  @override
  String toString() => 'AuthException: $message';
}
```

## Troubleshooting

### Common Issues

#### 1. Token Expiration

**Problem**: Getting 401 errors on API requests.

**Solution**:
```javascript
// Check token expiration
function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return Date.now() / 1000 > payload.exp;
  } catch {
    return true;
  }
}

// Implement automatic refresh
async function makeRequest(url, options = {}) {
  if (isTokenExpired(accessToken)) {
    await refreshToken();
  }
  
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`
    }
  });
}
```

#### 2. Rate Limiting

**Problem**: Getting 429 errors during login attempts.

**Solution**:
- Wait 15 minutes before retrying
- Implement exponential backoff
- Check for account lockout

```javascript
async function loginWithRetry(username, password, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await auth.login(username, password);
    } catch (error) {
      if (error.status === 429) {
        const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
  throw new Error('Max login attempts exceeded');
}
```

#### 3. Password Validation

**Problem**: Registration fails with password validation errors.

**Solution**:
```javascript
function validatePassword(password) {
  const errors = [];
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }
  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\?]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}
```

#### 4. BYOK API Key Issues

**Problem**: OpenRouter API key validation fails.

**Solutions**:
1. **Check key format**: Should start with `sk-or-v1-`
2. **Verify account balance**: Ensure sufficient credits
3. **Check rate limits**: OpenRouter may be rate limiting
4. **Test key directly**: Try the key on OpenRouter's API

```javascript
async function validateOpenRouterKey(apiKey) {
  try {
    const response = await fetch('https://openrouter.ai/api/v1/models', {
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      return {
        valid: true,
        models: data.data?.length || 0
      };
    } else {
      return {
        valid: false,
        error: `HTTP ${response.status}: ${response.statusText}`
      };
    }
  } catch (error) {
    return {
      valid: false,
      error: error.message
    };
  }
}
```

### Debug Checklist

1. **Network Connectivity**
   - Can you reach the API endpoint?
   - Are you using HTTPS in production?
   - Check for CORS issues in browser

2. **Token Format**
   - Is the token properly formatted?
   - Are you including "Bearer " prefix?
   - Is the token base64url encoded?

3. **Request Headers**
   - Content-Type: application/json
   - Authorization: Bearer <token>
   - Proper HTTP method

4. **Response Analysis**
   - Check HTTP status codes
   - Read error messages in response body
   - Look for validation errors

5. **Server Logs**
   - Check API server logs for errors
   - Monitor authentication failures
   - Review rate limiting logs

This comprehensive authentication guide provides developers with everything needed to implement secure authentication with the DevPocket API and leverage the BYOK model for AI services.