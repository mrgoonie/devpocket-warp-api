# DevPocket API Endpoints Documentation

**Status:** Production Ready ✅  
**Last Updated:** 2025-08-17  
**API Version:** 1.0.0  

This document provides a comprehensive overview of all DevPocket API endpoints. For the complete OpenAPI 3.0 specification, see `/docs/openapi.yaml`.

## Recent Updates
- ✅ All code quality checks passing (Black, Ruff, MyPy)
- ✅ Test infrastructure verified and working
- ✅ New AI service endpoints added
- ✅ Enhanced security with account locking
- ✅ WebSocket protocol fully documented
- ✅ **NEW**: Complete sync services architecture implemented
- ✅ **NEW**: Multi-device synchronization with conflict resolution
- ✅ **NEW**: Real-time sync notifications via WebSocket/Redis PubSub
- ✅ **NEW**: Command, SSH Profile, and Settings sync services
- ✅ **NEW**: Advanced conflict resolution strategies

---

# OpenAPI 3.0 Specification

openapi: 3.0.0
info:
  title: DevPocket API
  description: AI-Powered Mobile Terminal Backend API
  version: 1.0.0
  contact:
    name: DevPocket Support
    email: support@devpocket.app
    url: https://devpocket.app
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://api.devpocket.app
    description: Production server
  - url: https://staging-api.devpocket.app
    description: Staging server
  - url: http://localhost:8000
    description: Development server

tags:
  - name: Authentication
    description: User authentication and authorization
  - name: Terminal
    description: Terminal operations and command execution
  - name: AI
    description: AI-powered features and suggestions
  - name: Sync
    description: Cross-device synchronization
  - name: User
    description: User profile and settings
  - name: Subscription
    description: Subscription and billing
  - name: Database
    description: Database management and administration
  - name: Development
    description: Development and testing utilities

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        username:
          type: string
        subscription_tier:
          type: string
          enum: [free, pro, team, enterprise]
        created_at:
          type: string
          format: date-time
          
    Session:
      type: object
      properties:
        id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        device_id:
          type: string
        device_type:
          type: string
          enum: [ios, android, web]
        created_at:
          type: string
          format: date-time
          
    Command:
      type: object
      properties:
        id:
          type: string
          format: uuid
        session_id:
          type: string
          format: uuid
        command:
          type: string
        output:
          type: string
        status:
          type: string
          enum: [pending, running, success, error]
        exit_code:
          type: integer
        created_at:
          type: string
          format: date-time
        executed_at:
          type: string
          format: date-time
          
    AIRequest:
      type: object
      required:
        - prompt
      properties:
        prompt:
          type: string
          description: Natural language prompt
        context:
          type: array
          items:
            type: object
            properties:
              role:
                type: string
                enum: [user, assistant, system]
              content:
                type: string
        model:
          type: string
          default: claude-3-haiku
          enum: [claude-3-haiku, gpt-4o-mini, gpt-4o]
          
    AIResponse:
      type: object
      properties:
        suggestion:
          type: string
        explanation:
          type: string
        confidence:
          type: number
          format: float
          minimum: 0
          maximum: 1
        tokens_used:
          type: integer
          
    Error:
      type: object
      properties:
        code:
          type: string
        message:
          type: string
        details:
          type: object
          
    SyncConflict:
      type: object
      required:
        - conflict_id
        - conflict_type
        - local_data
        - remote_data
        - timestamp
      properties:
        conflict_id:
          type: string
          description: Unique identifier for the conflict
        conflict_type:
          type: string
          enum: [version_mismatch, concurrent_modification, data_corruption, schema_mismatch]
          description: Type of synchronization conflict
        data_type:
          type: string
          enum: [ssh_profiles, commands, settings, ai_preferences]
          description: Type of data that has the conflict
        local_data:
          type: object
          description: Local version of the conflicted data
          additionalProperties: true
        remote_data:
          type: object
          description: Remote version of the conflicted data
          additionalProperties: true
        local_timestamp:
          type: string
          format: date-time
          description: When the local data was last modified
        remote_timestamp:
          type: string
          format: date-time
          description: When the remote data was last modified
        timestamp:
          type: string
          format: date-time
          description: When the conflict was detected
        device_info:
          type: object
          properties:
            local_device_id:
              type: string
            local_device_name:
              type: string
            remote_device_id:
              type: string
            remote_device_name:
              type: string
        resolution_options:
          type: array
          items:
            type: string
            enum: [local, remote, merge, manual]
          description: Available resolution strategies for this conflict

paths:
  # ============================================================================
  # AUTHENTICATION ENDPOINTS
  # ============================================================================
  
  /api/auth/register:
    post:
      tags:
        - Authentication
      summary: Register new user
      operationId: registerUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - email
                - username
                - password
              properties:
                email:
                  type: string
                  format: email
                username:
                  type: string
                  minLength: 3
                  maxLength: 30
                password:
                  type: string
                  minLength: 8
                device_id:
                  type: string
                device_type:
                  type: string
                  enum: [ios, android]
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: string
                    format: uuid
                  token:
                    type: string
                  token_type:
                    type: string
                  expires_in:
                    type: integer
        '400':
          description: Invalid input or user already exists
          
  /api/auth/login:
    post:
      tags:
        - Authentication
      summary: Login user
      operationId: loginUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - username
                - password
              properties:
                username:
                  type: string
                  description: Username or email
                password:
                  type: string
                device_id:
                  type: string
                device_type:
                  type: string
                  enum: [ios, android]
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: string
                    format: uuid
                  token:
                    type: string
                  token_type:
                    type: string
                  expires_in:
                    type: integer
        '401':
          description: Invalid credentials
          
  /api/auth/refresh:
    post:
      tags:
        - Authentication
      summary: Refresh access token
      operationId: refreshToken
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Token refreshed
          content:
            application/json:
              schema:
                type: object
                properties:
                  token:
                    type: string
                  expires_in:
                    type: integer
                    
  /api/auth/logout:
    post:
      tags:
        - Authentication
      summary: Logout user
      operationId: logoutUser
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Logout successful
          
  # ============================================================================
  # TERMINAL ENDPOINTS
  # ============================================================================
  
  /api/ssh/connect:
    post:
      tags:
        - Terminal
      summary: Connect to SSH server
      operationId: connectSSH
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - host
                - username
              properties:
                host:
                  type: string
                port:
                  type: integer
                  default: 22
                username:
                  type: string
                password:
                  type: string
                private_key:
                  type: string
                  description: Base64 encoded private key
                passphrase:
                  type: string
      responses:
        '200':
          description: SSH connection established
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    
  /api/ssh/profiles:
    get:
      tags:
        - Terminal
      summary: Get saved SSH profiles
      operationId: getSSHProfiles
      security:
        - bearerAuth: []
      responses:
        '200':
          description: List of SSH profiles
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: string
                    name:
                      type: string
                    host:
                      type: string
                    port:
                      type: integer
                    username:
                      type: string
                    
    post:
      tags:
        - Terminal
      summary: Save SSH profile
      operationId: saveSSHProfile
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
                - host
                - username
              properties:
                name:
                  type: string
                host:
                  type: string
                port:
                  type: integer
                username:
                  type: string
                private_key_id:
                  type: string
      responses:
        '201':
          description: Profile saved
          
  /api/commands/execute:
    post:
      tags:
        - Terminal
      summary: Execute terminal command
      operationId: executeCommand
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - command
              properties:
                command:
                  type: string
                session_id:
                  type: string
                  format: uuid
                timeout:
                  type: integer
                  default: 30
      responses:
        '200':
          description: Command executed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Command'
                
  /api/commands/history:
    get:
      tags:
        - Terminal
      summary: Get command history
      operationId: getCommandHistory
      security:
        - bearerAuth: []
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
            maximum: 1000
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
        - name: session_id
          in: query
          schema:
            type: string
            format: uuid
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, running, success, error]
        - name: search
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Command history retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  commands:
                    type: array
                    items:
                      $ref: '#/components/schemas/Command'
                  total:
                    type: integer
                  has_more:
                    type: boolean
                    
  /api/commands/{command_id}:
    get:
      tags:
        - Terminal
      summary: Get specific command
      operationId: getCommand
      security:
        - bearerAuth: []
      parameters:
        - name: command_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Command details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Command'
                
  /api/commands/{command_id}/rerun:
    post:
      tags:
        - Terminal
      summary: Rerun command
      operationId: rerunCommand
      security:
        - bearerAuth: []
      parameters:
        - name: command_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Command rerun initiated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Command'
                
  # ============================================================================
  # AI ENDPOINTS
  # ============================================================================
  
  /api/ai/suggest:
    post:
      tags:
        - AI
      summary: Get AI command suggestion (BYOK)
      operationId: getAISuggestion
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - prompt
                - api_key
              properties:
                prompt:
                  type: string
                  description: Natural language prompt
                api_key:
                  type: string
                  description: User's OpenRouter API key
                context:
                  type: array
                  items:
                    type: object
                model:
                  type: string
                  default: claude-3-haiku
      responses:
        '200':
          description: AI suggestion generated
          content:
            application/json:
              schema:
                type: object
                properties:
                  suggestion:
                    type: string
                  cached:
                    type: boolean
        '401':
          description: Invalid API key
        '429':
          description: Rate limited by OpenRouter
          
  /api/ai/explain:
    post:
      tags:
        - AI
      summary: Explain command error (BYOK)
      operationId: explainError
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - command
                - error
                - api_key
              properties:
                command:
                  type: string
                error:
                  type: string
                api_key:
                  type: string
                  description: User's OpenRouter API key
      responses:
        '200':
          description: Error explanation generated
          content:
            application/json:
              schema:
                type: object
                properties:
                  explanation:
                    type: string
                  suggestions:
                    type: array
                    items:
                      type: string
                      
  /api/ai/validate-key:
    post:
      tags:
        - AI
      summary: Validate OpenRouter API key
      operationId: validateApiKey
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - api_key
              properties:
                api_key:
                  type: string
                  description: OpenRouter API key to validate
      responses:
        '200':
          description: Validation result
          content:
            application/json:
              schema:
                type: object
                properties:
                  valid:
                    type: boolean
                  models:
                    type: array
                    items:
                      type: string
                    description: Available models for this key
                    description: Available models for this key
                      
  /api/ai/complete:
    post:
      tags:
        - AI
      summary: Autocomplete command (BYOK)
      operationId: autocompleteCommand
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - partial_command
                - api_key
              properties:
                partial_command:
                  type: string
                api_key:
                  type: string
                  description: User's OpenRouter API key
                context:
                  type: array
                  items:
                    type: string
      responses:
        '200':
          description: Autocomplete suggestions
          content:
            application/json:
              schema:
                type: object
                properties:
                  completions:
                    type: array
                    items:
                      type: string
                    
  # ============================================================================
  # SYNC ENDPOINTS
  # ============================================================================
  
  /api/sync/data:
    get:
      tags:
        - Sync
      summary: Get synchronization data
      operationId: getSyncData
      security:
        - bearerAuth: []
      parameters:
        - name: data_types
          in: query
          required: true
          schema:
            type: array
            items:
              type: string
              enum: [ssh_profiles, sessions, commands, settings, ai_preferences, all]
          description: Types of data to synchronize
        - name: device_id
          in: query
          required: true
          schema:
            type: string
          description: Unique device identifier
        - name: device_name
          in: query
          required: true
          schema:
            type: string
          description: Human-readable device name
        - name: last_sync_timestamp
          in: query
          schema:
            type: string
            format: date-time
          description: Last synchronization timestamp
        - name: include_deleted
          in: query
          schema:
            type: boolean
            default: false
          description: Include deleted items in sync
      responses:
        '200':
          description: Sync data retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: object
                    additionalProperties:
                      type: array
                      items:
                        type: object
                    description: Synchronized data by type
                  sync_timestamp:
                    type: string
                    format: date-time
                    description: Current sync timestamp
                  total_items:
                    type: integer
                    description: Total items synchronized
                  conflicts:
                    type: array
                    items:
                      type: object
                      properties:
                        conflict_id:
                          type: string
                        conflict_type:
                          type: string
                          enum: [version_mismatch, concurrent_modification, data_corruption]
                        local_data:
                          type: object
                        remote_data:
                          type: object
                        timestamp:
                          type: string
                          format: date-time
                    description: Synchronization conflicts requiring resolution
                  device_count:
                    type: integer
                    description: Number of devices for this user
                  conflict_type:
                    type: string
                    nullable: true
                    description: Type of conflict if any
        '403':
          description: Sync not available for current subscription tier
        '429':
          description: Sync rate limit exceeded
          
    post:
      tags:
        - Sync
      summary: Upload synchronization data
      operationId: uploadSyncData
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              description: Synchronization data payload
              additionalProperties: true
              example:
                ssh_profiles:
                  - id: "profile-1"
                    name: "Production Server"
                    host: "prod.example.com"
                    username: "deploy"
                    modified_at: "2023-01-01T12:00:00Z"
                settings:
                  theme: "dark"
                  terminal_font_size: 14
                  ai_model_preference: "claude-3-haiku"
                device_id: "device-abc123"
                sync_timestamp: "2023-01-01T12:00:00Z"
      responses:
        '200':
          description: Sync data uploaded successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: "Sync data uploaded successfully"
                  timestamp:
                    type: string
                    format: date-time
                  conflicts_detected:
                    type: array
                    items:
                      type: object
                    description: Any conflicts that need resolution
        '409':
          description: Sync conflicts detected - manual resolution required
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: "Sync conflicts detected"
                  conflicts:
                    type: array
                    items:
                      $ref: '#/components/schemas/SyncConflict'
  
  /api/sync/stats:
    get:
      tags:
        - Sync
      summary: Get synchronization statistics
      operationId: getSyncStats
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Sync statistics retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_syncs:
                    type: integer
                    description: Total sync operations performed
                  successful_syncs:
                    type: integer
                    description: Number of successful syncs
                  failed_syncs:
                    type: integer
                    description: Number of failed sync attempts
                  last_sync:
                    type: string
                    format: date-time
                    nullable: true
                    description: Timestamp of last sync operation
                  active_devices:
                    type: integer
                    description: Number of currently active devices
                  total_conflicts:
                    type: integer
                    description: Total conflicts encountered
                  resolved_conflicts:
                    type: integer
                    description: Number of conflicts successfully resolved
                    
  /api/sync/conflicts/{conflict_id}/resolve:
    post:
      tags:
        - Sync
      summary: Resolve synchronization conflict
      operationId: resolveSyncConflict
      security:
        - bearerAuth: []
      parameters:
        - name: conflict_id
          in: path
          required: true
          schema:
            type: string
          description: Unique conflict identifier
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - resolution
              properties:
                resolution:
                  type: string
                  enum: [local, remote, merge]
                  description: "Resolution strategy: local (keep local data), remote (use remote data), merge (combine both)"
                resolved_data:
                  type: object
                  nullable: true
                  description: Resolved data when using merge strategy
                  additionalProperties: true
      responses:
        '200':
          description: Conflict resolved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                    example: "Conflict resolved successfully"
                  resolution_method:
                    type: string
                    description: Method used to resolve the conflict
                  final_data:
                    type: object
                    description: Final synchronized data after resolution
        '404':
          description: Conflict not found
        '400':
          description: Invalid resolution strategy
          
  # ============================================================================
  # USER ENDPOINTS
  # ============================================================================
  
  /api/user/profile:
    get:
      tags:
        - User
      summary: Get user profile
      operationId: getUserProfile
      security:
        - bearerAuth: []
      responses:
        '200':
          description: User profile
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
                
    put:
      tags:
        - User
      summary: Update user profile
      operationId: updateUserProfile
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                email:
                  type: string
                  format: email
      responses:
        '200':
          description: Profile updated
          
  /api/user/devices:
    get:
      tags:
        - User
      summary: Get user devices
      operationId: getUserDevices
      security:
        - bearerAuth: []
      responses:
        '200':
          description: List of devices
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    device_id:
                      type: string
                    device_type:
                      type: string
                    device_name:
                      type: string
                    last_active:
                      type: string
                      format: date-time
                      
  # ============================================================================
  # SUBSCRIPTION ENDPOINTS
  # ============================================================================
  
  /api/subscription/plans:
    get:
      tags:
        - Subscription
      summary: Get available plans
      operationId: getSubscriptionPlans
      responses:
        '200':
          description: List of plans
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    plan_id:
                      type: string
                    name:
                      type: string
                    price:
                      type: number
                    features:
                      type: array
                      items:
                        type: string
                        
  /api/subscription/current:
    get:
      tags:
        - Subscription
      summary: Get current subscription
      operationId: getCurrentSubscription
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Current subscription details
          content:
            application/json:
              schema:
                type: object
                properties:
                  plan_id:
                    type: string
                  status:
                    type: string
                  current_period_end:
                    type: string
                    format: date-time
                  cancel_at_period_end:
                    type: boolean
                    
  # ============================================================================
  # DATABASE MANAGEMENT ENDPOINTS
  # ============================================================================
  
  /api/admin/database/status:
    get:
      tags:
        - Database
      summary: Get database status and migration info
      operationId: getDatabaseStatus
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Database status information
          content:
            application/json:
              schema:
                type: object
                properties:
                  current_revision:
                    type: string
                    description: Current database revision
                  target_revision:
                    type: string
                    description: Target/latest revision
                  pending_migrations:
                    type: integer
                    description: Number of pending migrations
                  is_up_to_date:
                    type: boolean
                  last_migration_date:
                    type: string
                    format: date-time
                  migration_history:
                    type: array
                    items:
                      type: object
                      properties:
                        revision:
                          type: string
                        message:
                          type: string
                        date:
                          type: string
                          format: date-time
        '403':
          description: Admin access required
          
  /api/admin/database/migrate:
    post:
      tags:
        - Database
      summary: Run database migrations
      operationId: runMigrations
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                target:
                  type: string
                  default: head
                  description: Migration target (head, +1, -1, or revision ID)
                dry_run:
                  type: boolean
                  default: false
                  description: Preview migrations without executing
                skip_backup:
                  type: boolean
                  default: false
                  description: Skip automatic backup creation
                force:
                  type: boolean
                  default: false
                  description: Skip confirmation prompts
      responses:
        '200':
          description: Migration completed successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  message:
                    type: string
                  migrations_applied:
                    type: array
                    items:
                      type: string
                  backup_created:
                    type: string
                    description: Backup file path if created
        '400':
          description: Invalid migration target or parameters
        '403':
          description: Admin access required
        '500':
          description: Migration failed
          
  /api/admin/database/seed:
    post:
      tags:
        - Database
      summary: Seed database with test data
      operationId: seedDatabase
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                seed_type:
                  type: string
                  enum: [all, users, ssh, commands, sessions, sync]
                  default: all
                  description: Type of data to seed
                count:
                  type: integer
                  default: 10
                  minimum: 1
                  maximum: 10000
                  description: Number of records to create per type
                clean_first:
                  type: boolean
                  default: false
                  description: Clean existing data before seeding
                use_upsert:
                  type: boolean
                  default: false
                  description: Use upsert for conflict resolution
                environment:
                  type: string
                  enum: [development, testing, staging]
                  default: development
                  description: Environment context for seeding
      responses:
        '200':
          description: Database seeded successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  message:
                    type: string
                  records_created:
                    type: object
                    properties:
                      users:
                        type: integer
                      ssh_profiles:
                        type: integer
                      ssh_keys:
                        type: integer
                      commands:
                        type: integer
                      sessions:
                        type: integer
                      sync_data:
                        type: integer
                  execution_time:
                    type: number
                    description: Seeding execution time in seconds
        '400':
          description: Invalid seeding parameters
        '403':
          description: Admin access required
        '500':
          description: Seeding failed
          
  /api/admin/database/stats:
    get:
      tags:
        - Database
      summary: Get database statistics
      operationId: getDatabaseStats
      security:
        - bearerAuth: []
      responses:
        '200':
          description: Database statistics
          content:
            application/json:
              schema:
                type: object
                properties:
                  table_stats:
                    type: array
                    items:
                      type: object
                      properties:
                        table_name:
                          type: string
                        live_rows:
                          type: integer
                        inserts:
                          type: integer
                        updates:
                          type: integer
                        deletes:
                          type: integer
                        dead_rows:
                          type: integer
                  database_size:
                    type: string
                    description: Total database size
                  total_tables:
                    type: integer
                  last_updated:
                    type: string
                    format: date-time
        '403':
          description: Admin access required
          
  /api/admin/database/backup:
    post:
      tags:
        - Database
      summary: Create database backup
      operationId: createDatabaseBackup
      security:
        - bearerAuth: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                backup_name:
                  type: string
                  description: Custom backup name (optional)
                include_data:
                  type: boolean
                  default: true
                  description: Include data in backup
                compress:
                  type: boolean
                  default: true
                  description: Compress backup file
      responses:
        '200':
          description: Backup created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  backup_file:
                    type: string
                    description: Path to backup file
                  file_size:
                    type: string
                    description: Backup file size
                  created_at:
                    type: string
                    format: date-time
        '403':
          description: Admin access required
        '500':
          description: Backup creation failed
          
  /api/admin/database/reset:
    post:
      tags:
        - Database
      summary: Reset database (dangerous operation)
      operationId: resetDatabase
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - confirmation
              properties:
                confirmation:
                  type: string
                  description: Must be "RESET_DATABASE" to confirm
                backup_first:
                  type: boolean
                  default: true
                  description: Create backup before reset
                environment:
                  type: string
                  enum: [development, testing]
                  description: Only allowed in dev/test environments
      responses:
        '200':
          description: Database reset successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  message:
                    type: string
                  backup_created:
                    type: string
                    description: Backup file if created
        '400':
          description: Invalid confirmation or not allowed in this environment
        '403':
          description: Admin access required
        '500':
          description: Reset failed
          
  # ============================================================================
  # DEVELOPMENT UTILITIES ENDPOINTS
  # ============================================================================
  
  /api/dev/test-data/generate:
    post:
      tags:
        - Development
      summary: Generate test data for specific scenarios
      operationId: generateTestData
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                scenario:
                  type: string
                  enum: [user_onboarding, ssh_workflow, command_history, sync_testing, performance_testing]
                  description: Test scenario to generate data for
                parameters:
                  type: object
                  description: Scenario-specific parameters
                  properties:
                    user_count:
                      type: integer
                    command_count:
                      type: integer
                    session_duration_hours:
                      type: integer
                    ssh_profiles_per_user:
                      type: integer
      responses:
        '200':
          description: Test data generated successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  scenario:
                    type: string
                  data_created:
                    type: object
                  test_users:
                    type: array
                    items:
                      type: object
                      properties:
                        email:
                          type: string
                        password:
                          type: string
                        user_id:
                          type: string
        '400':
          description: Invalid scenario or parameters
        '403':
          description: Development environment only
          
  /api/dev/cleanup:
    post:
      tags:
        - Development
      summary: Clean up test data
      operationId: cleanupTestData
      security:
        - bearerAuth: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                older_than_hours:
                  type: integer
                  default: 24
                  description: Clean data older than specified hours
                include_test_users:
                  type: boolean
                  default: true
                  description: Include test users in cleanup
                data_types:
                  type: array
                  items:
                    type: string
                    enum: [users, commands, sessions, ssh_profiles]
      responses:
        '200':
          description: Cleanup completed
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  cleaned_records:
                    type: object
                    properties:
                      users:
                        type: integer
                      commands:
                        type: integer
                      sessions:
                        type: integer
                      ssh_profiles:
                        type: integer
        '403':
          description: Development environment only
                    
  # ============================================================================
  # WEBSOCKET ENDPOINT
  # ============================================================================
  
  /ws/terminal:
    get:
      tags:
        - Terminal
      summary: WebSocket terminal connection with SSH/PTY support
      operationId: websocketTerminal
      parameters:
        - name: token
          in: query
          required: true
          schema:
            type: string
      responses:
        '101':
          description: Switching Protocols
          headers:
            Upgrade:
              schema:
                type: string
                example: websocket
            Connection:
              schema:
                type: string
                example: Upgrade
                
      x-websocket-messages:
        client-to-server:
          - type: command
            description: Execute single command
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [command]
                data:
                  type: string
                  description: Command to execute
                  
          - type: connect_ssh
            description: Connect to SSH server
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [connect_ssh]
                config:
                  type: object
                  properties:
                    host:
                      type: string
                    port:
                      type: integer
                    username:
                      type: string
                    password:
                      type: string
                    key_path:
                      type: string
                      
          - type: create_pty
            description: Create local PTY session
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [create_pty]
                  
          - type: pty_input
            description: Send input to PTY
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [pty_input]
                data:
                  type: string
                  description: Input to send to PTY
                  
          - type: resize_pty
            description: Resize PTY window
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [resize_pty]
                cols:
                  type: integer
                rows:
                  type: integer
                  
          - type: ai_convert
            description: Convert natural language to command
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [ai_convert]
                prompt:
                  type: string
                api_key:
                  type: string
                  description: User's OpenRouter API key
                  
        server-to-client:
          - type: pty_output
            description: PTY output stream
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [pty_output]
                data:
                  type: string
                  
          - type: ssh_connected
            description: SSH connection established
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [ssh_connected]
                session_id:
                  type: string
                  
          - type: pty_created
            description: PTY session created
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [pty_created]
                session_id:
                  type: string
                  
          - type: ai_suggestion
            description: AI generated command
            payload:
              type: object
              properties:
                type:
                  type: string
                  enum: [ai_suggestion]
                command:
                  type: string