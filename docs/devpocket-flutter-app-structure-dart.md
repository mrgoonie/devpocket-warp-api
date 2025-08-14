// DevPocket Flutter App Structure
// Complete screen hierarchy and navigation flow

// ============================================================================
// APP STRUCTURE OVERVIEW
// ============================================================================

/*
DevPocket/
├── Authentication/
│   ├── SplashScreen
│   ├── OnboardingScreen
│   ├── LoginScreen
│   ├── RegisterScreen
│   ├── ForgotPasswordScreen
│   └── ResetPasswordScreen
│
├── Main App (TabNavigator)/
│   ├── Vaults/
│   │   ├── VaultsListScreen
│   │   ├── HostDetailsScreen
│   │   ├── KeychainScreen
│   │   └── LogsScreen
│   │
│   ├── Terminal/
│   │   ├── TerminalScreen (AI-Assisted)
│   │   ├── CommandBlocksView
│   │   └── QuickConnectSheet
│   │
│   ├── History/
│   │   ├── RecentConnectionsScreen
│   │   ├── CommandHistoryScreen
│   │   └── SessionDetailsScreen
│   │
│   ├── Code Editor (Coming Soon)/
│   │   └── ComingSoonScreen
│   │
│   └── Settings/
│       ├── ProfileScreen
│       ├── SubscriptionScreen
│       ├── PreferencesScreen
│       ├── SecurityScreen
│       └── SupportScreen
*/

// ============================================================================
// AUTHENTICATION SCREENS
// ============================================================================

// lib/screens/auth/splash_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lottie/lottie.dart';

class SplashScreen extends ConsumerStatefulWidget {
  @override
  _SplashScreenState createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuthStatus();
  }
  
  Future<void> _checkAuthStatus() async {
    await Future.delayed(Duration(seconds: 2));
    
    final isFirstLaunch = await _isFirstLaunch();
    final isLoggedIn = await _checkLoginStatus();
    
    if (isFirstLaunch) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => OnboardingScreen()),
      );
    } else if (isLoggedIn) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => MainTabScreen()),
      );
    } else {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => LoginScreen()),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFF0D1117),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Logo Animation
            Container(
              width: 120,
              height: 120,
              child: Lottie.asset('assets/animations/logo.json'),
            ),
            SizedBox(height: 24),
            Text(
              'DevPocket',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).primaryColor,
              ),
            ),
            SizedBox(height: 8),
            Text(
              'Your Terminal, Your Pocket',
              style: TextStyle(
                fontSize: 16,
                color: Colors.white60,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// lib/screens/auth/register_screen.dart
// ============================================================================

class RegisterScreen extends ConsumerStatefulWidget {
  @override
  _RegisterScreenState createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Back Button
                IconButton(
                  icon: Icon(Icons.arrow_back),
                  onPressed: () => Navigator.pop(context),
                ),
                
                SizedBox(height: 32),
                
                // Title
                Text(
                  'Create Account',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Start your 7-day free trial',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white60,
                  ),
                ),
                
                SizedBox(height: 48),
                
                // Email Field
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(
                    labelText: 'Email',
                    prefixIcon: Icon(Icons.email_outlined),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your email';
                    }
                    if (!value.contains('@')) {
                      return 'Please enter a valid email';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 16),
                
                // Username Field
                TextFormField(
                  controller: _usernameController,
                  decoration: InputDecoration(
                    labelText: 'Username',
                    prefixIcon: Icon(Icons.person_outline),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a username';
                    }
                    if (value.length < 3) {
                      return 'Username must be at least 3 characters';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 16),
                
                // Password Field
                TextFormField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword 
                            ? Icons.visibility_off 
                            : Icons.visibility,
                      ),
                      onPressed: () {
                        setState(() {
                          _obscurePassword = !_obscurePassword;
                        });
                      },
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a password';
                    }
                    if (value.length < 8) {
                      return 'Password must be at least 8 characters';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 32),
                
                // Register Button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _handleRegister,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).primaryColor,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: _isLoading
                        ? CircularProgressIndicator(color: Colors.white)
                        : Text(
                            'Start Free Trial',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  ),
                ),
                
                SizedBox(height: 24),
                
                // Login Link
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('Already have an account? '),
                    TextButton(
                      onPressed: () {
                        Navigator.pushReplacement(
                          context,
                          MaterialPageRoute(builder: (_) => LoginScreen()),
                        );
                      },
                      child: Text('Login'),
                    ),
                  ],
                ),
                
                SizedBox(height: 24),
                
                // Terms
                Text(
                  'By creating an account, you agree to our Terms of Service and Privacy Policy',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white60,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
  
  Future<void> _handleRegister() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isLoading = true);
    
    try {
      await ref.read(authProvider.notifier).register(
        email: _emailController.text,
        username: _usernameController.text,
        password: _passwordController.text,
      );
      
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => MainTabScreen()),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
}

// ============================================================================
// lib/screens/auth/login_screen.dart
// ============================================================================

class LoginScreen extends ConsumerStatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(height: 48),
                
                // Logo
                Center(
                  child: Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: Theme.of(context).primaryColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Icon(
                      Icons.terminal,
                      size: 48,
                      color: Colors.white,
                    ),
                  ),
                ),
                
                SizedBox(height: 48),
                
                // Title
                Text(
                  'Welcome Back',
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Login to continue',
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white60,
                  ),
                ),
                
                SizedBox(height: 48),
                
                // Username/Email Field
                TextFormField(
                  controller: _usernameController,
                  decoration: InputDecoration(
                    labelText: 'Username or Email',
                    prefixIcon: Icon(Icons.person_outline),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your username or email';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 16),
                
                // Password Field
                TextFormField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword 
                            ? Icons.visibility_off 
                            : Icons.visibility,
                      ),
                      onPressed: () {
                        setState(() {
                          _obscurePassword = !_obscurePassword;
                        });
                      },
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your password';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 12),
                
                // Forgot Password
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => ForgotPasswordScreen()),
                      );
                    },
                    child: Text('Forgot Password?'),
                  ),
                ),
                
                SizedBox(height: 24),
                
                // Login Button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _handleLogin,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).primaryColor,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: _isLoading
                        ? CircularProgressIndicator(color: Colors.white)
                        : Text(
                            'Login',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  ),
                ),
                
                SizedBox(height: 24),
                
                // Register Link
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text("Don't have an account? "),
                    TextButton(
                      onPressed: () {
                        Navigator.pushReplacement(
                          context,
                          MaterialPageRoute(builder: (_) => RegisterScreen()),
                        );
                      },
                      child: Text('Start Free Trial'),
                    ),
                  ],
                ),
                
                SizedBox(height: 32),
                
                // Social Login
                Row(
                  children: [
                    Expanded(child: Divider()),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 16),
                      child: Text('OR', style: TextStyle(color: Colors.white60)),
                    ),
                    Expanded(child: Divider()),
                  ],
                ),
                
                SizedBox(height: 24),
                
                // Social Buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildSocialButton(
                      icon: 'assets/icons/github.svg',
                      label: 'GitHub',
                      onPressed: _handleGitHubLogin,
                    ),
                    _buildSocialButton(
                      icon: 'assets/icons/google.svg',
                      label: 'Google',
                      onPressed: _handleGoogleLogin,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildSocialButton({
    required String icon,
    required String label,
    required VoidCallback onPressed,
  }) {
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: SvgPicture.asset(icon, width: 24, height: 24),
      label: Text(label),
      style: OutlinedButton.styleFrom(
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
  
  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isLoading = true);
    
    try {
      await ref.read(authProvider.notifier).login(
        username: _usernameController.text,
        password: _passwordController.text,
      );
      
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => MainTabScreen()),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
}

// ============================================================================
// lib/screens/auth/reset_password_screen.dart
// ============================================================================

class ResetPasswordScreen extends StatefulWidget {
  final String resetToken;
  
  const ResetPasswordScreen({required this.resetToken});
  
  @override
  _ResetPasswordScreenState createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _isLoading = false;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Reset Password'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Create New Password',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Enter your new password below',
                  style: TextStyle(color: Colors.white60),
                ),
                
                SizedBox(height: 32),
                
                // New Password
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'New Password',
                    prefixIcon: Icon(Icons.lock_outline),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a password';
                    }
                    if (value.length < 8) {
                      return 'Password must be at least 8 characters';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 16),
                
                // Confirm Password
                TextFormField(
                  controller: _confirmPasswordController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'Confirm Password',
                    prefixIcon: Icon(Icons.lock_outline),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  validator: (value) {
                    if (value != _passwordController.text) {
                      return 'Passwords do not match';
                    }
                    return null;
                  },
                ),
                
                SizedBox(height: 32),
                
                // Reset Button
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _handleReset,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Theme.of(context).primaryColor,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: _isLoading
                        ? CircularProgressIndicator(color: Colors.white)
                        : Text('Reset Password'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
  
  Future<void> _handleReset() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _isLoading = true);
    
    try {
      // Call API to reset password
      // await authService.resetPassword(widget.resetToken, _passwordController.text);
      
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => LoginScreen()),
        (route) => false,
      );
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Password reset successfully')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }
}

// ============================================================================
// MAIN TAB SCREEN
// ============================================================================

// lib/screens/main_tab_screen.dart
class MainTabScreen extends ConsumerStatefulWidget {
  @override
  _MainTabScreenState createState() => _MainTabScreenState();
}

class _MainTabScreenState extends ConsumerState<MainTabScreen> {
  int _currentIndex = 0;
  
  final List<Widget> _screens = [
    VaultsScreen(),
    TerminalScreen(),
    HistoryScreen(),
    ComingSoonScreen(feature: 'Code Editor'),
    SettingsScreen(),
  ];
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        type: BottomNavigationBarType.fixed,
        selectedItemColor: Theme.of(context).primaryColor,
        unselectedItemColor: Colors.white60,
        items: [
          BottomNavigationBarItem(
            icon: Icon(Icons.folder_special),
            label: 'Vaults',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.terminal),
            label: 'Terminal',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history),
            label: 'History',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.code),
            label: 'Editor',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// VAULTS SCREEN
// ============================================================================

// lib/screens/vaults/vaults_screen.dart
class VaultsScreen extends ConsumerStatefulWidget {
  @override
  _VaultsScreenState createState() => _VaultsScreenState();
}

class _VaultsScreenState extends ConsumerState<VaultsScreen> 
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Vaults'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: 'Hosts'),
            Tab(text: 'Keychain'),
            Tab(text: 'Logs'),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.add),
            onPressed: _showAddHostDialog,
          ),
        ],
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildHostsTab(),
          _buildKeychainTab(),
          _buildLogsTab(),
        ],
      ),
    );
  }
  
  Widget _buildHostsTab() {
    final hosts = ref.watch(hostsProvider);
    
    if (hosts.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.computer, size: 64, color: Colors.white30),
            SizedBox(height: 16),
            Text('No hosts configured'),
            SizedBox(height: 8),
            ElevatedButton.icon(
              onPressed: _showAddHostDialog,
              icon: Icon(Icons.add),
              label: Text('Add Host'),
            ),
          ],
        ),
      );
    }
    
    return ListView.builder(
      padding: EdgeInsets.all(16),
      itemCount: hosts.length,
      itemBuilder: (context, index) {
        final host = hosts[index];
        return Card(
          margin: EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: _getHostStatusColor(host.status),
              child: Icon(Icons.computer, color: Colors.white),
            ),
            title: Text(host.name),
            subtitle: Text('${host.username}@${host.hostname}:${host.port}'),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  icon: Icon(Icons.edit),
                  onPressed: () => _editHost(host),
                ),
                IconButton(
                  icon: Icon(Icons.play_arrow),
                  onPressed: () => _connectToHost(host),
                ),
              ],
            ),
            onTap: () => _showHostDetails(host),
          ),
        );
      },
    );
  }
  
  Widget _buildKeychainTab() {
    final keys = ref.watch(keychainProvider);
    
    return ListView.builder(
      padding: EdgeInsets.all(16),
      itemCount: keys.length,
      itemBuilder: (context, index) {
        final key = keys[index];
        return Card(
          margin: EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: Icon(Icons.key, color: Theme.of(context).primaryColor),
            title: Text(key.name),
            subtitle: Text(key.type),
            trailing: PopupMenuButton(
              itemBuilder: (context) => [
                PopupMenuItem(
                  child: Text('Copy Public Key'),
                  value: 'copy',
                ),
                PopupMenuItem(
                  child: Text('Export'),
                  value: 'export',
                ),
                PopupMenuItem(
                  child: Text('Delete'),
                  value: 'delete',
                ),
              ],
              onSelected: (value) => _handleKeyAction(key, value),
            ),
          ),
        );
      },
    );
  }
  
  Widget _buildLogsTab() {
    final logs = ref.watch(connectionLogsProvider);
    
    return ListView.builder(
      padding: EdgeInsets.all(16),
      itemCount: logs.length,
      itemBuilder: (context, index) {
        final log = logs[index];
        return Card(
          margin: EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: Icon(
              log.success ? Icons.check_circle : Icons.error,
              color: log.success ? Colors.green : Colors.red,
            ),
            title: Text(log.hostname),
            subtitle: Text(
              '${log.timestamp.toString()}\n${log.message}',
            ),
            isThreeLine: true,
            trailing: IconButton(
              icon: Icon(Icons.replay),
              onPressed: () => _retryConnection(log),
            ),
          ),
        );
      },
    );
  }
  
  void _showAddHostDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => AddHostSheet(),
    );
  }
  
  void _connectToHost(Host host) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TerminalScreen(host: host),
      ),
    );
  }
}

// ============================================================================
// TERMINAL SCREEN (AI-ASSISTED, BLOCK-BASED)
// ============================================================================

// Already implemented in previous artifact with updates for:
// - PTY support
// - Dual input modes (Command/Agent)
// - Block-based UI like Warp.dev
// - BYOK for AI features

// ============================================================================
// HISTORY SCREEN
// ============================================================================

// lib/screens/history/history_screen.dart
class HistoryScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recentConnections = ref.watch(recentConnectionsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: Text('History'),
        actions: [
          IconButton(
            icon: Icon(Icons.search),
            onPressed: () => _showSearchDialog(context),
          ),
          IconButton(
            icon: Icon(Icons.filter_list),
            onPressed: () => _showFilterDialog(context),
          ),
        ],
      ),
      body: ListView.builder(
        padding: EdgeInsets.all(16),
        itemCount: recentConnections.length,
        itemBuilder: (context, index) {
          final connection = recentConnections[index];
          return Card(
            margin: EdgeInsets.only(bottom: 12),
            child: InkWell(
              onTap: () => _showConnectionDetails(context, connection),
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.computer, size: 20),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            connection.hostname,
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                            ),
                          ),
                        ),
                        Text(
                          _formatTime(connection.timestamp),
                          style: TextStyle(
                            color: Colors.white60,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Duration: ${_formatDuration(connection.duration)}',
                      style: TextStyle(color: Colors.white70),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Commands: ${connection.commandCount}',
                      style: TextStyle(color: Colors.white70),
                    ),
                    if (connection.lastCommand != null) ...[
                      SizedBox(height: 8),
                      Container(
                        padding: EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.black26,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '\$ ${connection.lastCommand}',
                          style: TextStyle(
                            fontFamily: 'JetBrainsMono',
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                    SizedBox(height: 12),
                    Row(
                      children: [
                        OutlinedButton.icon(
                          onPressed: () => _reconnect(context, connection),
                          icon: Icon(Icons.replay, size: 16),
                          label: Text('Reconnect'),
                        ),
                        SizedBox(width: 8),
                        OutlinedButton.icon(
                          onPressed: () => _viewCommands(context, connection),
                          icon: Icon(Icons.list, size: 16),
                          label: Text('Commands'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
  
  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);
    
    if (difference.inMinutes < 60) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}h ago';
    } else {
      return '${difference.inDays}d ago';
    }
  }
  
  String _formatDuration(Duration duration) {
    if (duration.inMinutes < 60) {
      return '${duration.inMinutes} min';
    } else {
      return '${duration.inHours}h ${duration.inMinutes % 60}m';
    }
  }
}

// ============================================================================
// SETTINGS SCREEN
// ============================================================================

// lib/screens/settings/settings_screen.dart
class SettingsScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final isDarkMode = ref.watch(themeProvider) == ThemeMode.dark;
    
    return Scaffold(
      appBar: AppBar(
        title: Text('Settings'),
      ),
      body: ListView(
        children: [
          // Profile Section
          _buildSectionHeader('Account'),
          ListTile(
            leading: CircleAvatar(
              backgroundImage: user?.avatarUrl != null 
                  ? NetworkImage(user!.avatarUrl!)
                  : null,
              child: user?.avatarUrl == null 
                  ? Icon(Icons.person)
                  : null,
            ),
            title: Text(user?.username ?? 'Guest'),
            subtitle: Text(user?.email ?? ''),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _navigateTo(context, ProfileScreen()),
          ),
          
          // Subscription
          ListTile(
            leading: Icon(Icons.diamond),
            title: Text('Subscription'),
            subtitle: Text(_getSubscriptionStatus(user)),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _navigateTo(context, SubscriptionScreen()),
          ),
          
          Divider(),
          
          // Preferences Section
          _buildSectionHeader('Preferences'),
          
          // Terminal Theme
          ListTile(
            leading: Icon(Icons.color_lens),
            title: Text('Terminal Theme'),
            subtitle: Text(ref.watch(terminalThemeProvider).name),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _showTerminalThemeDialog(context, ref),
          ),
          
          // Font
          ListTile(
            leading: Icon(Icons.text_fields),
            title: Text('Terminal Font'),
            subtitle: Text('${ref.watch(fontFamilyProvider)} - ${ref.watch(fontSizeProvider)}pt'),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _showFontSettingsDialog(context, ref),
          ),
          
          // App Theme
          ListTile(
            leading: Icon(Icons.brightness_6),
            title: Text('App Theme'),
            trailing: SegmentedButton<ThemeMode>(
              segments: [
                ButtonSegment(
                  value: ThemeMode.light,
                  icon: Icon(Icons.light_mode, size: 16),
                ),
                ButtonSegment(
                  value: ThemeMode.dark,
                  icon: Icon(Icons.dark_mode, size: 16),
                ),
                ButtonSegment(
                  value: ThemeMode.system,
                  icon: Icon(Icons.auto_awesome, size: 16),
                ),
              ],
              selected: {ref.watch(themeProvider)},
              onSelectionChanged: (value) {
                ref.read(themeProvider.notifier).setTheme(value.first);
              },
            ),
          ),
          
          Divider(),
          
          // Security Section
          _buildSectionHeader('Security'),
          
          // Face ID / Touch ID
          if (Platform.isIOS) ...[
            SwitchListTile(
              secondary: Icon(Icons.face),
              title: Text('Face ID / Touch ID'),
              subtitle: Text('Use biometric authentication'),
              value: ref.watch(biometricEnabledProvider),
              onChanged: (value) => _toggleBiometric(ref, value),
            ),
          ],
          
          // Change Password
          ListTile(
            leading: Icon(Icons.lock),
            title: Text('Change Password'),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _navigateTo(context, ChangePasswordScreen()),
          ),
          
          // Two-Factor Auth
          ListTile(
            leading: Icon(Icons.security),
            title: Text('Two-Factor Authentication'),
            subtitle: Text(user?.twoFactorEnabled ?? false ? 'Enabled' : 'Disabled'),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _navigateTo(context, TwoFactorScreen()),
          ),
          
          Divider(),
          
          // Support Section
          _buildSectionHeader('Support'),
          
          // Discord
          ListTile(
            leading: SvgPicture.asset('assets/icons/discord.svg', width: 24),
            title: Text('Discord Community'),
            trailing: Icon(Icons.open_in_new),
            onTap: () => _openUrl('https://discord.gg/devpocket'),
          ),
          
          // Facebook
          ListTile(
            leading: Icon(Icons.facebook),
            title: Text('Facebook Group'),
            trailing: Icon(Icons.open_in_new),
            onTap: () => _openUrl('https://facebook.com/groups/devpocket'),
          ),
          
          // X (Twitter)
          ListTile(
            leading: SvgPicture.asset('assets/icons/x.svg', width: 24),
            title: Text('Follow on X'),
            trailing: Icon(Icons.open_in_new),
            onTap: () => _openUrl('https://x.com/devpocketapp'),
          ),
          
          // Documentation
          ListTile(
            leading: Icon(Icons.book),
            title: Text('Documentation'),
            trailing: Icon(Icons.open_in_new),
            onTap: () => _openUrl('https://docs.devpocket.app'),
          ),
          
          Divider(),
          
          // Legal Section
          _buildSectionHeader('Legal'),
          
          // Terms of Use
          ListTile(
            leading: Icon(Icons.description),
            title: Text('Terms of Use'),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _openUrl('https://devpocket.app/terms'),
          ),
          
          // Privacy Policy
          ListTile(
            leading: Icon(Icons.privacy_tip),
            title: Text('Privacy Policy'),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _openUrl('https://devpocket.app/privacy'),
          ),
          
          Divider(),
          
          // Rate App
          ListTile(
            leading: Icon(Icons.star, color: Colors.amber),
            title: Text('Rate DevPocket'),
            subtitle: Text('Love the app? Let us know!'),
            trailing: Icon(Icons.chevron_right),
            onTap: () => _rateApp(),
          ),
          
          // Version
          ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Version'),
            subtitle: Text('1.0.0 (Build 100)'),
          ),
          
          SizedBox(height: 20),
          
          // Logout Button
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: OutlinedButton.icon(
              onPressed: () => _handleLogout(context, ref),
              icon: Icon(Icons.logout, color: Colors.red),
              label: Text('Logout', style: TextStyle(color: Colors.red)),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: Colors.red),
                padding: EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
          
          SizedBox(height: 40),
        ],
      ),
    );
  }
  
  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Colors.white60,
        ),
      ),
    );
  }
  
  String _getSubscriptionStatus(User? user) {
    if (user == null) return 'Not logged in';
    if (user.isInTrial) {
      final daysLeft = user.trialEndsAt.difference(DateTime.now()).inDays;
      return 'Trial - $daysLeft days left';
    }
    switch (user.subscriptionTier) {
      case 'pro':
        return 'Pro - Monthly';
      case 'team':
        return 'Team - Monthly';
      case 'enterprise':
        return 'Enterprise';
      default:
        return 'Limited Access';
    }
  }
  
  void _handleLogout(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Logout'),
        content: Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              await ref.read(authProvider.notifier).logout();
              Navigator.pushAndRemoveUntil(
                context,
                MaterialPageRoute(builder: (_) => LoginScreen()),
                (route) => false,
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
            ),
            child: Text('Logout'),
          ),
        ],
      ),
    );
  }
}

// ============================================================================
// SUBSCRIPTION SCREEN
// ============================================================================

// lib/screens/settings/subscription_screen.dart
class SubscriptionScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final isInTrial = user?.isInTrial ?? false;
    final daysLeft = user?.trialEndsAt.difference(DateTime.now()).inDays ?? 0;
    
    return Scaffold(
      appBar: AppBar(
        title: Text('Subscription'),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Current Status
            if (isInTrial) ...[
              Container(
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.orange),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.timer, color: Colors.orange),
                        SizedBox(width: 8),
                        Text(
                          'Free Trial',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Colors.orange,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 8),
                    Text('$daysLeft days remaining'),
                    SizedBox(height: 4),
                    Text(
                      'Enjoy full Pro features during your trial',
                      style: TextStyle(color: Colors.white60),
                    ),
                  ],
                ),
              ),
              SizedBox(height: 24),
            ],
            
            // Pro Plan
            _buildPlanCard(
              context: context,
              title: 'Pro',
              price: '\$12',
              period: 'per month',
              features: [
                'Unlimited SSH connections',
                'Multi-device sync (up to 5)',
                'Cloud command history',
                'AI features with BYOK',
                'SSH profile management',
                'Priority support',
              ],
              isCurrentPlan: user?.subscriptionTier == 'pro',
              onSubscribe: () => _subscribeToPlan(context, 'pro'),
            ),
            
            SizedBox(height: 16),
            
            // Team Plan
            _buildPlanCard(
              context: context,
              title: 'Team',
              price: '\$25',
              period: 'per user/month',
              features: [
                'Everything in Pro',
                'Unlimited devices',
                'Team workspaces',
                'Shared workflows',
                'Admin dashboard',
                'SSO integration',
                'Dedicated support',
              ],
              isCurrentPlan: user?.subscriptionTier == 'team',
              onSubscribe: () => _subscribeToPlan(context, 'team'),
            ),
            
            SizedBox(height: 24),
            
            // Payment Methods
            if (user?.subscriptionTier != null) ...[
              Text(
                'Payment Method',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 12),
              Card(
                child: ListTile(
                  leading: Icon(Icons.credit_card),
                  title: Text('•••• •••• •••• 4242'),
                  subtitle: Text('Expires 12/25'),
                  trailing: TextButton(
                    onPressed: () => _updatePaymentMethod(context),
                    child: Text('Update'),
                  ),
                ),
              ),
              
              SizedBox(height: 24),
              
              // Billing History
              Text(
                'Billing History',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 12),
              Card(
                child: Column(
                  children: [
                    _buildInvoiceItem('Aug 1, 2025', '\$12.00', 'Paid'),
                    _buildInvoiceItem('Jul 1, 2025', '\$12.00', 'Paid'),
                    _buildInvoiceItem('Jun 1, 2025', '\$12.00', 'Paid'),
                  ],
                ),
              ),
              
              SizedBox(height: 24),
              
              // Cancel Subscription
              Center(
                child: TextButton(
                  onPressed: () => _cancelSubscription(context),
                  child: Text(
                    'Cancel Subscription',
                    style: TextStyle(color: Colors.red),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  Widget _buildPlanCard({
    required BuildContext context,
    required String title,
    required String price,
    required String period,
    required List<String> features,
    required bool isCurrentPlan,
    required VoidCallback onSubscribe,
  }) {
    return Card(
      elevation: isCurrentPlan ? 8 : 2,
      child: Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: isCurrentPlan 
              ? Border.all(color: Theme.of(context).primaryColor, width: 2)
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (isCurrentPlan) ...[
                  SizedBox(width: 8),
                  Chip(
                    label: Text('Current Plan'),
                    backgroundColor: Theme.of(context).primaryColor,
                  ),
                ],
              ],
            ),
            SizedBox(height: 8),
            Row(
              baseline: TextBaseline.alphabetic,
              crossAxisAlignment: CrossAxisAlignment.baseline,
              children: [
                Text(
                  price,
                  style: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(width: 8),
                Text(
                  period,
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white60,
                  ),
                ),
              ],
            ),
            SizedBox(height: 16),
            ...features.map((feature) => Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Icon(Icons.check, color: Colors.green, size: 20),
                  SizedBox(width: 8),
                  Expanded(child: Text(feature)),
                ],
              ),
            )),
            SizedBox(height: 16),
            if (!isCurrentPlan)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onSubscribe,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).primaryColor,
                    padding: EdgeInsets.symmetric(vertical: 12),
                  ),
                  child: Text('Subscribe'),
                ),
              ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildInvoiceItem(String date, String amount, String status) {
    return ListTile(
      title: Text(date),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(amount),
          SizedBox(width: 8),
          Chip(
            label: Text(status),
            backgroundColor: Colors.green.withOpacity(0.2),
          ),
        ],
      ),
    );
  }
}