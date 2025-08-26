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
      NavigationService.navigateToReplacement(AppRoutes.home);
    });

    return Scaffold(
      backgroundColor: Color(0xFFF3F4F6), // fixed hex color
      body: Center(child: Image.asset('assets/images/logo-with-bg.png')),
    );
  }
}
