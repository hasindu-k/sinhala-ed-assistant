import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/auth_controller.dart';
import '../routes/app_routes.dart';
import '../routes/navigation_service.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();

    return Scaffold(
      appBar: AppBar(title: const Text("Login")),
      body: Center(
        child: ElevatedButton(
          onPressed: () {
            auth.signIn("test@example.com", "password");
            NavigationService.navigateToReplacement(AppRoutes.home);
          },
          child: const Text("Login → Home"),
        ),
      ),
    );
  }
}
