import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../presentation/controllers/exit_controller.dart';
import '../controller/auth_controller.dart';
import '../../../presentation/routes/app_routes.dart';
import '../../../presentation/routes/navigation_service.dart';
import '../../../core/widgets/app_widgets.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

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
        if (NavigationService.navigatorKey.currentState!.canPop()) {
          NavigationService.goBack();
        } else {
          _exit.handleSystemBack(context, didPop, result);
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
              const VSpace(24),
              const AppLogo(height: 100),
              const VSpace(64),
              AppTextField(
                controller: _emailController,
                label: "Email",
                keyboardType: TextInputType.emailAddress,
              ),
              const VSpace(12),
              PasswordField(controller: _passwordController),
              const VSpace(24),
              LoadingButton(
                isLoading: _isLoading,
                onPressed: _login,
                label: 'Login',
              ),
              const VSpace(16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text("Don't have an account? "),
                  LinkText(
                    text: 'Register',
                    onTap: () => NavigationService.navigateToReplacement(
                        AppRoutes.register),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
