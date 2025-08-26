import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/theme.dart';
import '../controllers/auth_controller.dart';
import '../routes/app_routes.dart';
import '../routes/navigation_service.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  @override
  void initState() {
    super.initState();
    _navigateNext();
  }

  void _navigateNext() async {
    await Future.delayed(const Duration(seconds: 2));

    final authController = context.read<AuthController>();
    final isLoggedIn = authController.currentUser != null;

    if (isLoggedIn) {
      NavigationService.navigateToReplacement(AppRoutes.home);
    } else {
      NavigationService.navigateToReplacement(AppRoutes.login);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ThemeUtils.getSplashBackgroundColor(context),
      body: Center(
        child: Theme.of(context).brightness == Brightness.dark
            ? Image.asset('assets/images/logo-with-dark-bg.png')
            : Image.asset('assets/images/logo-with-bg.png'),
      ),
    );
  }
}
