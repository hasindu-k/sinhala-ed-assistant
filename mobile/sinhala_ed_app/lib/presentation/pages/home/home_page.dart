// lib/presentation/pages/home/home_page.dart
import 'package:flutter/material.dart';
import '../../controllers/exit_controller.dart';
import '../../routes/app_routes.dart';
import '../../../core/theme/theme.dart';
import 'widgets/welcome_section.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _exit = ExitController();

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        _exit.handleSystemBack(context, didPop, result);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Sinhala Ed Assistant'),
          automaticallyImplyLeading: false,
          actions: [
            IconButton(
              onPressed: () => Navigator.pushNamed(context, AppRoutes.profile),
              icon: const Icon(Icons.person),
              tooltip: 'Profile',
            ),
          ],
        ),
        body: const WelcomeSection(),
      ),
    );
  }
}
