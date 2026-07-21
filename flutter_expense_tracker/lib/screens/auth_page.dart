import 'dart:convert';
import 'dart:ui';
import 'package:http/http.dart' as http;

import 'package:flutter/material.dart';

import '../widgets/auth_text_field.dart';
import 'dashboard_page.dart';

enum AuthMode { login, register }

class AuthPage extends StatefulWidget {
  const AuthPage({super.key});

  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  AuthMode _mode = AuthMode.login;
  bool _rememberMe = true;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  bool _isLoading = false;

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() {
      _isLoading = true;
    });

    final url = _mode == AuthMode.register 
        ? 'http://10.0.2.2:8000/api/register' 
        : 'http://10.0.2.2:8000/api/login';
        
    try {
      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': _emailController.text.trim(),
          'password': _passwordController.text,
        }),
      );
      
      final data = jsonDecode(response.body);
      
      if (response.statusCode == 200) {
        if (_mode == AuthMode.register) {
          _showMessage('Account created successfully. Please login.');
          setState(() {
            _mode = AuthMode.login;
          });
        } else {
          _showMessage('Login successful');
          final userId = data['user']['id'];
          final username = data['user']['username'];
          
          if (!mounted) return;
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => DashboardPage(userId: userId, username: username),
            ),
          );
        }
      } else {
        _showMessage(data['detail'] ?? 'Authentication failed');
      }
    } catch (e) {
      _showMessage('Network error: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  String? _required(String? value, String label) {
    if (value == null || value.trim().isEmpty) {
      return '$label is required';
    }
    return null;
  }

  Widget _buildFeatureChip(String text, IconData icon) {
    return Container(
      margin: const EdgeInsets.only(right: 8, bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: Colors.white),
          const SizedBox(width: 8),
          Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeroPanel(BuildContext context, bool compact) {
    return Container(
      constraints: BoxConstraints(minHeight: compact ? 260 : 620),
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0F172A), Color(0xFF134E4A), Color(0xFF0F766E)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(28),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -40,
            top: -30,
            child: Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.08),
              ),
            ),
          ),
          Positioned(
            left: -20,
            bottom: -40,
            child: Container(
              width: 140,
              height: 140,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFFF59E0B).withValues(alpha: 0.18),
              ),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: const Text(
                      'Expense Tracker',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  const Text(
                    'Track spending with a clean, secure dashboard.',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 36,
                      height: 1.05,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Sign in or create an account to upload documents, inspect charts, filter transactions, and save every update per user.',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.82),
                      fontSize: 16,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
              Wrap(
                children: [
                  _buildFeatureChip(
                    'Per-user DB storage',
                    Icons.storage_rounded,
                  ),
                  _buildFeatureChip(
                    'Insights & charts',
                    Icons.query_stats_rounded,
                  ),
                  _buildFeatureChip(
                    'Upload and edit docs',
                    Icons.upload_file_rounded,
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildFormPanel(BuildContext context) {
    final isRegister = _mode == AuthMode.register;

    return ClipRRect(
      borderRadius: BorderRadius.circular(28),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: Colors.white.withValues(alpha: 0.4)),
          ),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Welcome back',
                  style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                Text(
                  isRegister
                      ? 'Create your account to start tracking expenses.'
                      : 'Log in to continue to your expense dashboard.',
                  style: TextStyle(color: Colors.grey.shade700, height: 1.4),
                ),
                const SizedBox(height: 20),
                ToggleButtons(
                  isSelected: [
                    _mode == AuthMode.login,
                    _mode == AuthMode.register,
                  ],
                  borderRadius: BorderRadius.circular(16),
                  onPressed: (index) {
                    setState(() {
                      _mode = index == 0 ? AuthMode.login : AuthMode.register;
                    });
                  },
                  children: const [
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 18),
                      child: Text('Login'),
                    ),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 18),
                      child: Text('Register'),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                if (isRegister) ...[
                  AuthTextField(
                    controller: _nameController,
                    label: 'Full name',
                    icon: Icons.person_rounded,
                    textInputAction: TextInputAction.next,
                    validator: (value) => _required(value, 'Full name'),
                  ),
                  const SizedBox(height: 14),
                ],
                AuthTextField(
                  controller: _emailController,
                  label: 'Email / Username',
                  icon: Icons.email_rounded,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  validator: (value) => _required(value, 'Email / Username'),
                ),
                const SizedBox(height: 14),
                AuthTextField(
                  controller: _passwordController,
                  label: 'Password',
                  icon: Icons.lock_rounded,
                  obscureText: true,
                  textInputAction: isRegister
                      ? TextInputAction.next
                      : TextInputAction.done,
                  validator: (value) => _required(value, 'Password'),
                  onFieldSubmitted: (_) {
                    if (!isRegister) _submit();
                  },
                ),
                if (isRegister) ...[
                  const SizedBox(height: 14),
                  AuthTextField(
                    controller: _confirmPasswordController,
                    label: 'Confirm password',
                    icon: Icons.lock_outline_rounded,
                    obscureText: true,
                    textInputAction: TextInputAction.done,
                    validator: (value) {
                      if (_required(value, 'Confirm password') != null) {
                        return 'Confirm password is required';
                      }
                      if (value != _passwordController.text) {
                        return 'Passwords do not match';
                      }
                      return null;
                    },
                    onFieldSubmitted: (_) => _submit(),
                  ),
                ],
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Switch.adaptive(
                            value: _rememberMe,
                            onChanged: (value) => setState(() => _rememberMe = value),
                          ),
                          const SizedBox(width: 8),
                          Flexible(
                            child: Text(
                              'Remember me',
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(color: Colors.grey.shade800),
                            ),
                          ),
                        ],
                      ),
                    ),

                    if (!isRegister)
                      TextButton(
                        onPressed: () =>
                            _showMessage('Password reset flow coming soon.'),
                        child: const Text('Forgot password?'),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                FilledButton(
                  onPressed: _isLoading ? null : _submit,
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    textStyle: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  child: _isLoading 
                      ? const SizedBox(
                          height: 20, 
                          width: 20, 
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)
                        )
                      : Text(isRegister ? 'Create account' : 'Sign in'),
                ),
                const SizedBox(height: 14),
                Text(
                  'This screen is ready to connect to your backend API for real authentication.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFFF4F7FA), Color(0xFFE9F9F5)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
          ),
          Positioned(
            left: -40,
            top: 40,
            child: Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF0F766E).withValues(alpha: 0.08),
              ),
            ),
          ),
          Positioned(
            right: -30,
            bottom: 20,
            child: Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFFF59E0B).withValues(alpha: 0.10),
              ),
            ),
          ),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth > 960;
                    final content = isWide
                        ? Row(
                            children: [
                              Expanded(
                                flex: 5,
                                child: _buildHeroPanel(context, false),
                              ),
                              const SizedBox(width: 24),
                              Expanded(
                                flex: 4,
                                child: _buildFormPanel(context),
                              ),
                            ],
                          )
                        : Column(
                            children: [
                              _buildHeroPanel(context, true),
                              const SizedBox(height: 20),
                              _buildFormPanel(context),
                            ],
                          );

                    return ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 1240),
                      child: content,
                    );
                  },
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
