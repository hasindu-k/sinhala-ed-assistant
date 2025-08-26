import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/exit_controller.dart';
import '../controllers/auth_controller.dart';
import '../routes/app_routes.dart';
import '../routes/navigation_service.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  // bool _rememberMe = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final auth = context.read<AuthController>();
    setState(() => _isLoading = true);

    try {
      await auth.signIn(
        _emailController.text.trim(),
        _passwordController.text,
        // rememberMe: _rememberMe,
      );
      if (auth.currentUser != null) {
        NavigationService.navigateToReplacement(AppRoutes.home);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Login failed: ${e.toString()}')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final _exit = ExitController();

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        // Check if Navigator can pop
        if (NavigationService.navigatorKey.currentState!.canPop()) {
          NavigationService.goBack(); // Go to previous route
        } else {
          _exit.handleSystemBack(context, didPop, result); // Exit
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text("Login"),
          automaticallyImplyLeading: false,
        ),
        body: SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                const SizedBox(height: 24),
                Image.asset(
                  'assets/images/logo.png',
                  height: 100,
                ),
                const SizedBox(height: 64),
                TextField(
                  controller: _emailController,
                  decoration: const InputDecoration(
                    labelText: "Email",
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: "Password",
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword
                            ? Icons.visibility
                            : Icons.visibility_off,
                      ),
                      onPressed: () {
                        setState(() {
                          _obscurePassword = !_obscurePassword;
                        });
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                _isLoading
                    ? const CircularProgressIndicator()
                    : SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: _login,
                          child: const Text(
                            "Login",
                            style: TextStyle(fontSize: 18),
                          ),
                        ),
                      ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text("Don't have an account? "),
                    GestureDetector(
                      onTap: () {
                        NavigationService.navigateTo(AppRoutes.register);
                      },
                      child: const Text(
                        "Register",
                        style: TextStyle(
                          color: Colors.blue,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            )),
      ),
    );
  }
}
