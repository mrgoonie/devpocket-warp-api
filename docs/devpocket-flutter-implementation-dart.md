// DevPocket Flutter App Implementation
// File: lib/main.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:xterm/xterm.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ============================================================================
// MAIN APP ENTRY
// ============================================================================

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.initialize();
  
  runApp(
    ProviderScope(
      child: DevPocketApp(),
    ),
  );
}

class DevPocketApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DevPocket',
      theme: AppTheme.darkTheme,
      home: TerminalScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

// ============================================================================
// CONFIGURATION
// ============================================================================

class AppConfig {
  static late SharedPreferences prefs;
  static const String apiBaseUrl = 'wss://api.devpocket.app';
  
  // BYOK - Bring Your Own Key for OpenRouter
  static String? get openRouterApiKey => prefs.getString('openrouter_api_key');
  static Future<void> setOpenRouterApiKey(String key) async {
    await prefs.setString('openrouter_api_key', key);
  }
  
  static Future<void> initialize() async {
    prefs = await SharedPreferences.getInstance();
  }
}

// ============================================================================
// THEME
// ============================================================================

class AppTheme {
  static final darkTheme = ThemeData(
    brightness: Brightness.dark,
    primaryColor: Color(0xFF00D4AA),
    scaffoldBackgroundColor: Color(0xFF0D1117),
    fontFamily: 'JetBrainsMono',
    colorScheme: ColorScheme.dark(
      primary: Color(0xFF00D4AA),
      secondary: Color(0xFF7C3AED),
      surface: Color(0xFF161B22),
      background: Color(0xFF0D1117),
    ),
  );
}

// ============================================================================
// TERMINAL SCREEN
// ============================================================================

class TerminalScreen extends ConsumerStatefulWidget {
  @override
  _TerminalScreenState createState() => _TerminalScreenState();
}

class _TerminalScreenState extends ConsumerState<TerminalScreen> {
  late Terminal terminal;
  late TerminalController terminalController;
  final TextEditingController commandController = TextEditingController();
  final ScrollController scrollController = ScrollController();
  final List<CommandBlock> commandBlocks = [];
  
  // Input modes
  InputMode inputMode = InputMode.command;
  
  // PTY session
  String? ptySessionId;
  
  @override
  void initState() {
    super.initState();
    initializeTerminal();
    connectWebSocket();
    checkApiKey();
  }
  
  void initializeTerminal() {
    terminal = Terminal(
      maxLines: 10000,
      onInput: _handleTerminalInput, // Direct PTY input
    );
    
    terminalController = TerminalController();
    
    terminal.onOutput = (String output) {
      handleTerminalOutput(output);
    };
  }
  
  void connectWebSocket() {
    final wsUrl = Uri.parse('${AppConfig.apiBaseUrl}/terminal');
    final channel = WebSocketChannel.connect(wsUrl);
    
    ref.read(webSocketProvider.notifier).connect(channel);
  }
  
  void checkApiKey() {
    if (AppConfig.openRouterApiKey == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _showApiKeyDialog();
      });
    }
  }
  
  // Handle direct terminal input (PTY)
  void _handleTerminalInput(String input) {
    if (ptySessionId != null) {
      ref.read(webSocketProvider.notifier).sendPtyInput(ptySessionId!, input);
    }
  }
  
  // Show API key setup dialog
  Future<void> _showApiKeyDialog() async {
    final keyController = TextEditingController();
    
    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text('Setup OpenRouter API Key'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('DevPocket uses BYOK (Bring Your Own Key) for AI features.'),
            SizedBox(height: 8),
            Text('Get your API key from openrouter.ai'),
            SizedBox(height: 16),
            TextField(
              controller: keyController,
              decoration: InputDecoration(
                labelText: 'OpenRouter API Key',
                hintText: 'sk-or-...',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
            },
            child: Text('Skip'),
          ),
          ElevatedButton(
            onPressed: () async {
              await AppConfig.setOpenRouterApiKey(keyController.text);
              Navigator.of(context).pop();
            },
            child: Text('Save'),
          ),
        ],
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    final aiSuggestions = ref.watch(aiSuggestionsProvider);
    
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // App Bar
            _buildAppBar(),
            
            // Terminal View
            Expanded(
              child: GestureDetector(
                onHorizontalDragEnd: _handleSwipe,
                child: _buildTerminalView(),
              ),
            ),
            
            // AI Suggestions Bar
            if (aiSuggestions.isNotEmpty)
              _buildAiSuggestionsBar(aiSuggestions),
            
            // Command Input
            _buildCommandInput(),
          ],
        ),
      ),
    );
  }
  
  Widget _buildAppBar() {
    return Container(
      height: 56,
      padding: EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(
            color: Colors.white.withOpacity(0.1),
          ),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.terminal, color: Theme.of(context).primaryColor),
          SizedBox(width: 12),
          Text(
            'DevPocket',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          Spacer(),
          IconButton(
            icon: Icon(Icons.add_box),
            onPressed: _createNewTab,
          ),
          IconButton(
            icon: Icon(Icons.sync),
            onPressed: _syncWithCloud,
          ),
          IconButton(
            icon: Icon(Icons.settings),
            onPressed: _openSettings,
          ),
        ],
      ),
    );
  }
  
  Widget _buildTerminalView() {
    return Container(
      color: Color(0xFF0D1117),
      child: Column(
        children: [
          // PTY Terminal View (Interactive)
          Container(
            height: 300,
            margin: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.black,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Theme.of(context).primaryColor),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: TerminalView(
                terminal,
                controller: terminalController,
                autofocus: true,
                backgroundOpacity: 0.95,
                onSecondaryTapDown: (details, offset) {
                  // Context menu for copy/paste
                  _showContextMenu(details.globalPosition);
                },
              ),
            ),
          ),
          
          // Command Blocks History
          Expanded(
            child: ListView.builder(
              controller: scrollController,
              padding: EdgeInsets.symmetric(horizontal: 16),
              itemCount: commandBlocks.length,
              itemBuilder: (context, index) {
                return CommandBlockWidget(
                  block: commandBlocks[index],
                  onRerun: () => _rerunCommand(index),
                  onShare: () => _shareCommand(index),
                  onAiExplain: () => _explainWithAi(index),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildAiSuggestionsBar(List<String> suggestions) {
    return Container(
      height: 40,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.symmetric(horizontal: 16),
        itemCount: suggestions.length,
        itemBuilder: (context, index) {
          return Padding(
            padding: EdgeInsets.only(right: 8),
            child: ActionChip(
              label: Text(suggestions[index]),
              onPressed: () => _applySuggestion(suggestions[index]),
              backgroundColor: Theme.of(context).colorScheme.secondary,
            ),
          );
        },
      ),
    );
  }
  
  Widget _buildCommandInput() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.1),
          ),
        ),
      ),
      child: Column(
        children: [
          // Mode Selector
          Row(
            children: [
              ChoiceChip(
                label: Text('Command Mode'),
                selected: inputMode == InputMode.command,
                onSelected: (selected) {
                  setState(() {
                    inputMode = InputMode.command;
                  });
                },
                selectedColor: Theme.of(context).primaryColor,
              ),
              SizedBox(width: 8),
              ChoiceChip(
                label: Row(
                  children: [
                    Icon(Icons.auto_awesome, size: 16),
                    SizedBox(width: 4),
                    Text('Agent Mode'),
                  ],
                ),
                selected: inputMode == InputMode.agent,
                onSelected: (selected) {
                  if (AppConfig.openRouterApiKey == null) {
                    _showApiKeyDialog();
                  } else {
                    setState(() {
                      inputMode = InputMode.agent;
                    });
                  }
                },
                selectedColor: Theme.of(context).colorScheme.secondary,
              ),
              Spacer(),
              IconButton(
                icon: Icon(Icons.settings),
                onPressed: _showApiKeyDialog,
                tooltip: 'API Settings',
              ),
            ],
          ),
          SizedBox(height: 8),
          // Input Field
          Row(
            children: [
              Icon(
                inputMode == InputMode.command 
                    ? Icons.terminal 
                    : Icons.auto_awesome,
                color: inputMode == InputMode.command 
                    ? Theme.of(context).primaryColor 
                    : Theme.of(context).colorScheme.secondary,
              ),
              SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: commandController,
                  style: TextStyle(
                    fontFamily: 'JetBrainsMono',
                    fontSize: 14,
                  ),
                  decoration: InputDecoration(
                    hintText: inputMode == InputMode.command
                        ? 'Enter command (e.g., ls -la, docker ps)'
                        : 'Describe what you want (e.g., "show running containers")',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                  ),
                  onSubmitted: _executeCommand,
                ),
              ),
              SizedBox(width: 8),
              IconButton(
                icon: Icon(Icons.send),
                color: inputMode == InputMode.command 
                    ? Theme.of(context).primaryColor
                    : Theme.of(context).colorScheme.secondary,
                onPressed: () => _executeCommand(commandController.text),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  void _executeCommand(String input) async {
    if (input.isEmpty) return;
    
    String command = input;
    
    // If in Agent Mode, convert natural language to command
    if (inputMode == InputMode.agent) {
      if (AppConfig.openRouterApiKey == null) {
        _showApiKeyDialog();
        return;
      }
      
      // Show loading indicator
      final block = CommandBlock(
        command: input,
        output: 'Converting to command...',
        timestamp: DateTime.now(),
        status: CommandStatus.running,
        isAgentGenerated: true,
      );
      
      setState(() {
        commandBlocks.add(block);
      });
      
      // Convert using AI
      try {
        command = await ref.read(aiProvider).convertToCommand(
          input,
          AppConfig.openRouterApiKey!,
        );
        
        // Update block with generated command
        block.command = command;
        block.output = '';
      } catch (e) {
        block.status = CommandStatus.error;
        block.output = 'Failed to convert: $e';
        setState(() {});
        return;
      }
    } else {
      // Add to command blocks for Command Mode
      final block = CommandBlock(
        command: command,
        output: '',
        timestamp: DateTime.now(),
        status: CommandStatus.running,
        isAgentGenerated: false,
      );
      
      setState(() {
        commandBlocks.add(block);
      });
    }
    
    // Send command via SSH
    ref.read(webSocketProvider.notifier).sendCommand(command);
    
    // Clear input
    commandController.clear();
    
    // Scroll to bottom
    scrollController.animateTo(
      scrollController.position.maxScrollExtent,
      duration: Duration(milliseconds: 300),
      curve: Curves.easeOut,
    );
  }
  
  void _handleSwipe(DragEndDetails details) {
    if (details.primaryVelocity! > 0) {
      // Swiped right - previous tab
      ref.read(tabProvider.notifier).previousTab();
    } else if (details.primaryVelocity! < 0) {
      // Swiped left - next tab
      ref.read(tabProvider.notifier).nextTab();
    }
  }
}

// ============================================================================
// COMMAND BLOCK WIDGET
// ============================================================================

class CommandBlockWidget extends StatefulWidget {
  final CommandBlock block;
  final VoidCallback onRerun;
  final VoidCallback onShare;
  final VoidCallback onAiExplain;
  
  const CommandBlockWidget({
    required this.block,
    required this.onRerun,
    required this.onShare,
    required this.onAiExplain,
  });
  
  @override
  _CommandBlockWidgetState createState() => _CommandBlockWidgetState();
}

class _CommandBlockWidgetState extends State<CommandBlockWidget> {
  bool isExpanded = true;
  
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _getBorderColor(),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          InkWell(
            onTap: () => setState(() => isExpanded = !isExpanded),
            child: Container(
              padding: EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(
                    isExpanded ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '\$ ${widget.block.command}',
                      style: TextStyle(
                        fontFamily: 'JetBrainsMono',
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).primaryColor,
                      ),
                    ),
                  ),
                  _buildStatusIcon(),
                ],
              ),
            ),
          ),
          
          // Output
          if (isExpanded && widget.block.output.isNotEmpty)
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Color(0xFF0D1117),
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(8),
                  bottomRight: Radius.circular(8),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SelectableText(
                    widget.block.output,
                    style: TextStyle(
                      fontFamily: 'JetBrainsMono',
                      fontSize: 13,
                      color: Colors.white70,
                    ),
                  ),
                  SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      IconButton(
                        icon: Icon(Icons.replay, size: 18),
                        onPressed: widget.onRerun,
                        tooltip: 'Rerun',
                      ),
                      IconButton(
                        icon: Icon(Icons.share, size: 18),
                        onPressed: widget.onShare,
                        tooltip: 'Share',
                      ),
                      IconButton(
                        icon: Icon(Icons.help_outline, size: 18),
                        onPressed: widget.onAiExplain,
                        tooltip: 'AI Explain',
                      ),
                    ],
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
  
  Color _getBorderColor() {
    switch (widget.block.status) {
      case CommandStatus.success:
        return Colors.green.withOpacity(0.5);
      case CommandStatus.error:
        return Colors.red.withOpacity(0.5);
      case CommandStatus.running:
        return Theme.of(context).primaryColor.withOpacity(0.5);
      default:
        return Colors.white.withOpacity(0.1);
    }
  }
  
  Widget _buildStatusIcon() {
    switch (widget.block.status) {
      case CommandStatus.success:
        return Icon(Icons.check_circle, color: Colors.green, size: 18);
      case CommandStatus.error:
        return Icon(Icons.error, color: Colors.red, size: 18);
      case CommandStatus.running:
        return SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation(Theme.of(context).primaryColor),
          ),
        );
      default:
        return SizedBox();
    }
  }
}

// ============================================================================
// MODELS
// ============================================================================

enum InputMode {
  command,  // Raw command mode
  agent,    // AI agent mode
}

class CommandBlock {
  String command;
  String output;
  final DateTime timestamp;
  CommandStatus status;
  final bool isAgentGenerated;
  
  CommandBlock({
    required this.command,
    required this.output,
    required this.timestamp,
    required this.status,
    this.isAgentGenerated = false,
  });
}

enum CommandStatus {
  running,
  success,
  error,
}

// ============================================================================
// PROVIDERS
// ============================================================================

final webSocketProvider = StateNotifierProvider<WebSocketNotifier, WebSocketState>((ref) {
  return WebSocketNotifier();
});

final aiSuggestionsProvider = StateProvider<List<String>>((ref) => []);

final tabProvider = StateNotifierProvider<TabNotifier, int>((ref) {
  return TabNotifier();
});

// ============================================================================
// WEBSOCKET NOTIFIER
// ============================================================================

class WebSocketNotifier extends StateNotifier<WebSocketState> {
  WebSocketChannel? _channel;
  
  WebSocketNotifier() : super(WebSocketState.disconnected);
  
  void connect(WebSocketChannel channel) {
    _channel = channel;
    state = WebSocketState.connected;
    
    _channel!.stream.listen(
      (data) => _handleMessage(data),
      onError: (error) => _handleError(error),
      onDone: () => _handleDisconnect(),
    );
  }
  
  void sendCommand(String command) {
    if (_channel != null && state == WebSocketState.connected) {
      _channel!.sink.add(json.encode({
        'type': 'command',
        'data': command,
      }));
    }
  }
  
  void sendPtyInput(String sessionId, String input) {
    if (_channel != null && state == WebSocketState.connected) {
      _channel!.sink.add(json.encode({
        'type': 'pty_input',
        'session_id': sessionId,
        'data': input,
      }));
    }
  }
  
  void createPtySession() {
    if (_channel != null && state == WebSocketState.connected) {
      _channel!.sink.add(json.encode({
        'type': 'create_pty',
      }));
    }
  }
  
  void _handleMessage(dynamic data) {
    // Handle incoming messages including PTY output
    final message = json.decode(data);
    if (message['type'] == 'pty_output') {
      // Handle PTY output
    } else if (message['type'] == 'pty_created') {
      // Store PTY session ID
    }
  }
  
  void _handleError(dynamic error) {
    state = WebSocketState.error;
  }
  
  void _handleDisconnect() {
    state = WebSocketState.disconnected;
  }
}

enum WebSocketState {
  connected,
  disconnected,
  error,
}

// ============================================================================
// TAB NOTIFIER
// ============================================================================

class TabNotifier extends StateNotifier<int> {
  TabNotifier() : super(0);
  
  void nextTab() {
    state = state + 1;
  }
  
  void previousTab() {
    if (state > 0) {
      state = state - 1;
    }
  }
  
  void selectTab(int index) {
    state = index;
  }
}