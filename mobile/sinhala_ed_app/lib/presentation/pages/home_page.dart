import 'package:flutter/material.dart';
import '../controllers/exit_controller.dart';
import '../routes/app_routes.dart';
import '../../core/theme/theme.dart';

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
      canPop: false, // Prevent default back navigation
      onPopInvokedWithResult: (didPop, result) {
        _exit.handleSystemBack(context, didPop, result);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Sinhala Ed Assistant'),
          automaticallyImplyLeading: false,
          actions: [
            IconButton(
              onPressed: () {
                Navigator.pushNamed(context, AppRoutes.profile);
              },
              icon: const Icon(Icons.person),
              tooltip: 'Profile',
            ),
          ],
        ),
        body: const _WelcomeSection(),
      ),
    );
  }
}

class _WelcomeSection extends StatelessWidget {
  const _WelcomeSection();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: ThemeUtils.getLargePadding(),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Title
            Text(
              'Welcome to Sinhala Ed Assistant',
              textAlign: TextAlign.center,
              style: AppTextStyles.displaySmall.copyWith(
                color: ThemeUtils.getTextColor(context),
              ),
            ),
            const SizedBox(height: 16),

            // Subtitle
            Text(
              'Your educational assistant is ready to help!',
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyLarge.copyWith(
                color: ThemeUtils.getSecondaryTextColor(context),
              ),
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
