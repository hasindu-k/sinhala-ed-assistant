import 'package:flutter/material.dart';
import '../routes/app_routes.dart';
import '../routes/navigation_service.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Login")),
      body: Center(
        child: ElevatedButton(
          onPressed: () {
            NavigationService.navigateToReplacement(AppRoutes.home);
          },
          child: const Text("Login → Home"),
        ),
      ),
    );
  }
}
