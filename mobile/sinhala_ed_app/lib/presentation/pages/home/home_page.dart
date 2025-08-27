// lib/presentation/pages/home/home_page.dart
import 'package:flutter/material.dart';
import '../../controllers/exit_controller.dart';
import '../../routes/app_routes.dart';
import '../../../core/theme/theme.dart';
import '../../../../data/models/feature_item.dart';
import 'widgets/feature_list.dart';
import 'widgets/tip_banner.dart';
import 'widgets/action_buttons.dart';

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
        body: const _WelcomeSection(),
      ),
    );
  }
}

class _WelcomeSection extends StatelessWidget {
  const _WelcomeSection();

  @override
  Widget build(BuildContext context) {
    final textColor = ThemeUtils.getTextColor(context);
    final secondary = ThemeUtils.getSecondaryTextColor(context);

    return Center(
      child: Padding(
        padding: ThemeUtils.getLargePadding(),
        child: SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Title
              Text(
                'Welcome to Sinhala Ed Assistant',
                textAlign: TextAlign.center,
                style: AppTextStyles.displaySmall.copyWith(color: textColor),
              ),
              const SizedBox(height: 12),

              // Subtitle
              Text(
                'Your bilingual educational copilot for Sinhala resources.',
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyLarge.copyWith(color: secondary),
              ),

              const SizedBox(height: 24),

              const TipBanner(
                icon: Icons.lightbulb,
                text:
                    'Tip: You can switch Light/Dark/System from Profile → Theme.',
              ),

              const SizedBox(height: 16),

              // Feature cards
              FeatureList(features: featureItems),

              const SizedBox(height: 20),

              const ActionButtonsRow(),
            ],
          ),
        ),
      ),
    );
  }
}
