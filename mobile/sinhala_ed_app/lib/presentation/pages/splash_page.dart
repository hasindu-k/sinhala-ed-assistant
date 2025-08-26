import 'package:flutter/material.dart';
import '../routes/app_routes.dart';
import '../routes/navigation_service.dart';

class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    Future.delayed(const Duration(seconds: 2), () {
      // bool isLoggedIn = false; // replace with your auth check
      // if (isLoggedIn) {
      //   Navigator.pushReplacementNamed(context, '/home');
      // } else {
      //   Navigator.pushReplacementNamed(context, '/login');
      // }
      NavigationService.navigateToReplacement(AppRoutes.login);
    });
    return const Scaffold(body: Center(child: Text("Splash Screen")));
  }
}
