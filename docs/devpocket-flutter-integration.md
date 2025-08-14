// DevPocket Flutter Integration Guide
// This file demonstrates how to integrate the Flutter app with the backend API

// ============================================================================
// API CLIENT
// File: lib/services/api_client.dart
// ============================================================================

import 'package:dio/dio.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:cookie_jar/cookie_jar.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  late Dio _dio;
  final FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String baseUrl = 'https://api.devpocket.app';
  
  ApiClient() {
    _initializeDio();
  }
  
  void _initializeDio() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: Duration(seconds: 5),
      receiveTimeout: Duration(seconds: 10),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));
    
    // Add cookie manager
    final cookieJar = CookieJar();
    _dio.interceptors.add(CookieManager(cookieJar));
    
    // Add auth interceptor
    _dio.interceptors.add(AuthInterceptor(_storage));
    
    // Add logging interceptor (for development)
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
    ));
  }
  
  // Auth endpoints
  Future<AuthResponse> register({
    required String email,
    required String username,
    required String password,
  }) async {
    try {
      final response = await _dio.post('/api/auth/register', data: {
        'email': email,
        'username': username,
        'password': password,
        'device_id': await _getDeviceId(),
        'device_type': _getDeviceType(),
      });
      
      final authResponse = AuthResponse.fromJson(response.data);
      await _saveToken(authResponse.token);
      return authResponse;
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<AuthResponse> login({
    required String username,
    required String password,
  }) async {
    try {
      final response = await _dio.post('/api/auth/login', data: {
        'username': username,
        'password': password,
        'device_id': await _getDeviceId(),
        'device_type': _getDeviceType(),
      });
      
      final authResponse = AuthResponse.fromJson(response.data);
      await _saveToken(authResponse.token);
      return authResponse;
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  // Command endpoints
  Future<Command> executeCommand(String command, {String? sessionId}) async {
    try {
      final response = await _dio.post('/api/commands/execute', data: {
        'command': command,
        'session_id': sessionId,
      });
      
      return Command.fromJson(response.data);
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<List<Command>> getCommandHistory({
    int limit = 100,
    int offset = 0,
    String? search,
  }) async {
    try {
      final response = await _dio.get('/api/commands/history', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (search != null) 'search': search,
      });
      
      return (response.data['commands'] as List)
          .map((json) => Command.fromJson(json))
          .toList();
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  // AI endpoints with BYOK
  Future<AiSuggestion> getAiSuggestion(String prompt, String apiKey, {List<Message>? context}) async {
    try {
      final response = await _dio.post('/api/ai/suggest', data: {
        'prompt': prompt,
        'api_key': apiKey,  // User's OpenRouter API key
        if (context != null) 'context': context.map((m) => m.toJson()).toList(),
      });
      
      return AiSuggestion.fromJson(response.data);
    } on DioError catch (e) {
      if (e.response?.statusCode == 401) {
        throw AppException('Invalid OpenRouter API key', code: 'INVALID_API_KEY');
      }
      throw _handleError(e);
    }
  }
  
  Future<ErrorExplanation> explainError(String command, String error, String apiKey) async {
    try {
      final response = await _dio.post('/api/ai/explain', data: {
        'command': command,
        'error': error,
        'api_key': apiKey,  // User's OpenRouter API key
      });
      
      return ErrorExplanation.fromJson(response.data);
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<bool> validateApiKey(String apiKey) async {
    try {
      final response = await _dio.post('/api/ai/validate-key', data: {
        'api_key': apiKey,
      });
      
      return response.data['valid'] ?? false;
    } on DioError catch (e) {
      return false;
    }
  }
  
  // SSH endpoints
  Future<String> connectSSH({
    required String host,
    required int port,
    required String username,
    String? password,
    String? privateKey,
  }) async {
    try {
      final response = await _dio.post('/api/ssh/connect', data: {
        'host': host,
        'port': port,
        'username': username,
        if (password != null) 'password': password,
        if (privateKey != null) 'private_key': privateKey,
      });
      
      return response.data['session_id'];
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  // Sync endpoints
  Future<SyncResult> syncCommands(List<Command> commands, DateTime lastSync) async {
    try {
      final response = await _dio.post('/api/sync/commands', data: {
        'commands': commands.map((c) => c.toJson()).toList(),
        'last_sync': lastSync.toIso8601String(),
      });
      
      return SyncResult.fromJson(response.data);
    } on DioError catch (e) {
      throw _handleError(e);
    }
  }
  
  // Helper methods
  Future<void> _saveToken(String token) async {
    await _storage.write(key: 'auth_token', value: token);
  }
  
  Future<String?> _getToken() async {
    return await _storage.read(key: 'auth_token');
  }
  
  Future<String> _getDeviceId() async {
    // Implementation depends on platform
    // Use device_info_plus package
    return 'device_id';
  }
  
  String _getDeviceType() {
    if (Platform.isIOS) return 'ios';
    if (Platform.isAndroid) return 'android';
    return 'unknown';
  }
  
  AppException _handleError(DioError error) {
    switch (error.type) {
      case DioErrorType.connectionTimeout:
      case DioErrorType.sendTimeout:
      case DioErrorType.receiveTimeout:
        return AppException('Connection timeout', code: 'TIMEOUT');
      case DioErrorType.connectionError:
        return AppException('No internet connection', code: 'NO_INTERNET');
      case DioErrorType.badResponse:
        final statusCode = error.response?.statusCode;
        final message = error.response?.data['message'] ?? 'Server error';
        return AppException(message, code: statusCode.toString());
      default:
        return AppException('An error occurred', code: 'UNKNOWN');
    }
  }
}

// ============================================================================
// AUTH INTERCEPTOR
// ============================================================================

class AuthInterceptor extends Interceptor {
  final FlutterSecureStorage storage;
  
  AuthInterceptor(this.storage);
  
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await storage.read(key: 'auth_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    super.onRequest(options, handler);
  }
  
  @override
  void onError(DioError err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Token expired, try to refresh
      // If refresh fails, redirect to login
    }
    super.onError(err, handler);
  }
}

// ============================================================================
// WEBSOCKET SERVICE
// File: lib/services/websocket_service.dart
// ============================================================================

import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

class WebSocketService {
  WebSocketChannel? _channel;
  final String baseUrl = 'wss://api.devpocket.app';
  final _messageController = StreamController<WebSocketMessage>.broadcast();
  String? _ptySessionId;
  
  Stream<WebSocketMessage> get messages => _messageController.stream;
  bool get isConnected => _channel != null;
  String? get ptySessionId => _ptySessionId;
  
  Future<void> connect(String token) async {
    try {
      final uri = Uri.parse('$baseUrl/ws/terminal?token=$token');
      _channel = WebSocketChannel.connect(uri);
      
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
      );
      
      print('WebSocket connected');
    } catch (e) {
      print('WebSocket connection error: $e');
      throw e;
    }
  }
  
  void sendCommand(String command) {
    if (_channel != null) {
      _channel!.sink.add(json.encode({
        'type': 'command',
        'data': command,
      }));
    }
  }
  
  void connectSSH(Map<String, dynamic> sshConfig) {
    if (_channel != null) {
      _channel!.sink.add(json.encode({
        'type': 'connect_ssh',
        'config': sshConfig,
      }));
    }
  }
  
  void createPtySession() {
    if (_channel != null) {
      _channel!.sink.add(json.encode({
        'type': 'create_pty',
      }));
    }
  }
  
  void sendPtyInput(String input) {
    if (_channel != null && _ptySessionId != null) {
      _channel!.sink.add(json.encode({
        'type': 'pty_input',
        'data': input,
      }));
    }
  }
  
  void resizePty(int cols, int rows) {
    if (_channel != null && _ptySessionId != null) {
      _channel!.sink.add(json.encode({
        'type': 'resize_pty',
        'cols': cols,
        'rows': rows,
      }));
    }
  }
  
  void convertToCommand(String prompt, String apiKey) {
    if (_channel != null) {
      _channel!.sink.add(json.encode({
        'type': 'ai_convert',
        'prompt': prompt,
        'api_key': apiKey,
      }));
    }
  }
  
  void killProcess() {
    if (_channel != null) {
      _channel!.sink.add(json.encode({
        'type': 'kill',
      }));
    }
  }
  
  void requestSync() {
    if (_channel != null) {
      _channel!.sink.add(json.encode({
        'type': 'sync',
      }));
    }
  }
  
  void _handleMessage(dynamic data) {
    try {
      final message = json.decode(data);
      
      // Handle PTY session creation
      if (message['type'] == 'pty_created' || message['type'] == 'ssh_connected') {
        _ptySessionId = message['session_id'];
      }
      
      _messageController.add(WebSocketMessage.fromJson(message));
    } catch (e) {
      print('Error parsing WebSocket message: $e');
    }
  }
  
  void _handleError(error) {
    print('WebSocket error: $error');
    _messageController.addError(error);
  }
  
  void _handleDisconnect() {
    print('WebSocket disconnected');
    _channel = null;
    _ptySessionId = null;
    // Implement reconnection logic here
    _reconnect();
  }
  
  Future<void> _reconnect() async {
    await Future.delayed(Duration(seconds: 3));
    // Get token and reconnect
    final token = await _getToken();
    if (token != null) {
      await connect(token);
    }
  }
  
  void disconnect() {
    _channel?.sink.close(status.goingAway);
    _channel = null;
    _ptySessionId = null;
  }
  
  void dispose() {
    disconnect();
    _messageController.close();
  }
}

// ============================================================================
// AI SERVICE
// File: lib/services/ai_service.dart
// ============================================================================

class AiService {
  final ApiClient _apiClient;
  final _suggestionsController = StreamController<List<String>>.broadcast();
  Timer? _debounceTimer;
  
  Stream<List<String>> get suggestions => _suggestionsController.stream;
  
  AiService(this._apiClient);
  
  void getSuggestionsForInput(String input, String? apiKey) {
    if (apiKey == null) {
      _suggestionsController.add([]);
      return;
    }
    
    // Debounce input
    _debounceTimer?.cancel();
    _debounceTimer = Timer(Duration(milliseconds: 300), () async {
      if (input.isEmpty) {
        _suggestionsController.add([]);
        return;
      }
      
      try {
        final suggestion = await _apiClient.getAiSuggestion(input, apiKey);
        _suggestionsController.add([suggestion.suggestion]);
      } catch (e) {
        print('Error getting AI suggestions: $e');
        _suggestionsController.add([]);
      }
    });
  }
  
  Future<String> convertNaturalLanguageToCommand(String prompt, String apiKey) async {
    try {
      final suggestion = await _apiClient.getAiSuggestion(
        prompt,
        apiKey,
        context: await _getRecentContext(),
      );
      return suggestion.suggestion;
    } catch (e) {
      if (e is AppException && e.code == 'INVALID_API_KEY') {
        throw AppException('Invalid OpenRouter API key. Please check your settings.');
      }
      throw AppException('Failed to convert to command');
    }
  }
  
  Future<String> explainError(String command, String error, String apiKey) async {
    try {
      final explanation = await _apiClient.explainError(command, error, apiKey);
      return explanation.explanation;
    } catch (e) {
      throw AppException('Failed to explain error');
    }
  }
  
  Future<bool> validateApiKey(String apiKey) async {
    return await _apiClient.validateApiKey(apiKey);
  }
  
  Future<List<Message>> _getRecentContext() async {
    // Get recent commands from local storage for context
    return [];
  }
  
  void dispose() {
    _debounceTimer?.cancel();
    _suggestionsController.close();
  }
}

// ============================================================================
// SYNC SERVICE
// File: lib/services/sync_service.dart
// ============================================================================

class SyncService {
  final ApiClient _apiClient;
  final Database _localDb;
  Timer? _syncTimer;
  bool _isSyncing = false;
  
  SyncService(this._apiClient, this._localDb);
  
  void startAutoSync() {
    _syncTimer = Timer.periodic(Duration(minutes: 5), (_) {
      syncCommands();
    });
  }
  
  Future<void> syncCommands() async {
    if (_isSyncing) return;
    
    _isSyncing = true;
    try {
      // Get unsynced commands from local database
      final unsyncedCommands = await _localDb.getUnsyncedCommands();
      final lastSync = await _getLastSyncTime();
      
      if (unsyncedCommands.isNotEmpty || _shouldSync(lastSync)) {
        final result = await _apiClient.syncCommands(unsyncedCommands, lastSync);
        
        // Update local database with synced data
        await _localDb.markCommandsSynced(unsyncedCommands);
        await _saveLastSyncTime(DateTime.now());
        
        print('Synced ${result.synced} commands');
      }
    } catch (e) {
      print('Sync error: $e');
    } finally {
      _isSyncing = false;
    }
  }
  
  bool _shouldSync(DateTime lastSync) {
    return DateTime.now().difference(lastSync).inMinutes > 5;
  }
  
  Future<DateTime> _getLastSyncTime() async {
    // Get from shared preferences
    return DateTime.now().subtract(Duration(hours: 1));
  }
  
  Future<void> _saveLastSyncTime(DateTime time) async {
    // Save to shared preferences
  }
  
  void stopAutoSync() {
    _syncTimer?.cancel();
  }
  
  void dispose() {
    stopAutoSync();
  }
}

// ============================================================================
// LOCAL DATABASE
// File: lib/services/local_database.dart
// ============================================================================

import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class LocalDatabase {
  Database? _database;
  
  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }
  
  Future<Database> _initDatabase() async {
    final path = join(await getDatabasesPath(), 'devpocket.db');
    
    return await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE commands (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            command TEXT NOT NULL,
            output TEXT,
            status TEXT,
            synced INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            executed_at TEXT
          )
        ''');
        
        await db.execute('''
          CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT
          )
        ''');
        
        await db.execute('''
          CREATE INDEX idx_commands_synced ON commands(synced);
        ''');
        
        await db.execute('''
          CREATE INDEX idx_commands_created ON commands(created_at);
        ''');
      },
    );
  }
  
  Future<void> saveCommand(Command command) async {
    final db = await database;
    await db.insert(
      'commands',
      command.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
  
  Future<List<Command>> getRecentCommands({int limit = 100}) async {
    final db = await database;
    final maps = await db.query(
      'commands',
      orderBy: 'created_at DESC',
      limit: limit,
    );
    
    return maps.map((map) => Command.fromMap(map)).toList();
  }
  
  Future<List<Command>> getUnsyncedCommands() async {
    final db = await database;
    final maps = await db.query(
      'commands',
      where: 'synced = ?',
      whereArgs: [0],
    );
    
    return maps.map((map) => Command.fromMap(map)).toList();
  }
  
  Future<void> markCommandsSynced(List<Command> commands) async {
    final db = await database;
    final batch = db.batch();
    
    for (final command in commands) {
      batch.update(
        'commands',
        {'synced': 1},
        where: 'id = ?',
        whereArgs: [command.id],
      );
    }
    
    await batch.commit();
  }
  
  Future<void> saveSetting(String key, String value) async {
    final db = await database;
    await db.insert(
      'settings',
      {'key': key, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
  
  Future<String?> getSetting(String key) async {
    final db = await database;
    final maps = await db.query(
      'settings',
      where: 'key = ?',
      whereArgs: [key],
    );
    
    if (maps.isNotEmpty) {
      return maps.first['value'] as String;
    }
    return null;
  }
}

// ============================================================================
// MODELS
// ============================================================================

class AuthResponse {
  final String userId;
  final String token;
  final String tokenType;
  final int expiresIn;
  
  AuthResponse({
    required this.userId,
    required this.token,
    required this.tokenType,
    required this.expiresIn,
  });
  
  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      userId: json['user_id'],
      token: json['token'],
      tokenType: json['token_type'],
      expiresIn: json['expires_in'],
    );
  }
}

class Command {
  final String id;
  final String sessionId;
  final String command;
  final String? output;
  final String status;
  final DateTime createdAt;
  final DateTime? executedAt;
  
  Command({
    required this.id,
    required this.sessionId,
    required this.command,
    this.output,
    required this.status,
    required this.createdAt,
    this.executedAt,
  });
  
  factory Command.fromJson(Map<String, dynamic> json) {
    return Command(
      id: json['id'],
      sessionId: json['session_id'],
      command: json['command'],
      output: json['output'],
      status: json['status'],
      createdAt: DateTime.parse(json['created_at']),
      executedAt: json['executed_at'] != null 
          ? DateTime.parse(json['executed_at']) 
          : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'session_id': sessionId,
      'command': command,
      'output': output,
      'status': status,
      'created_at': createdAt.toIso8601String(),
      'executed_at': executedAt?.toIso8601String(),
    };
  }
}

class WebSocketMessage {
  final String type;
  final dynamic data;
  
  WebSocketMessage({required this.type, required this.data});
  
  factory WebSocketMessage.fromJson(Map<String, dynamic> json) {
    return WebSocketMessage(
      type: json['type'],
      data: json['data'],
    );
  }
}

class AppException implements Exception {
  final String message;
  final String? code;
  
  AppException(this.message, {this.code});
  
  @override
  String toString() => 'AppException: $message (code: $code)';
}