import 'package:flutter/material.dart';
import 'core/theme/theme.dart';
import 'presentation/routes/app_routes.dart';
import 'presentation/routes/app_pages.dart';
import 'presentation/routes/navigation_service.dart';
import 'presentation/routes/route_generator.dart';

class SinhalaEdApp extends StatelessWidget {
  const SinhalaEdApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sinhala Ed Assistant',
      debugShowCheckedModeBanner: false,

      // Theme configuration
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,

      // Navigation configuration
      initialRoute: AppRoutes.splash,
      navigatorKey: NavigationService.navigatorKey,
      routes: AppPages.routes,
      onGenerateRoute: RouteGenerator.generateRoute,
    );
  }
}
