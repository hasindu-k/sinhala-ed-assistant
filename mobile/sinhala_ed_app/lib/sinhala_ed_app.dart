import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme/theme.dart';
import 'core/providers/theme_provider.dart';
import 'presentation/controllers/auth_controller.dart'; // 👈 add this
import 'presentation/routes/app_routes.dart';
import 'presentation/routes/app_pages.dart';
import 'presentation/routes/navigation_service.dart';
import 'presentation/routes/route_generator.dart';

class SinhalaEdApp extends StatelessWidget {
  const SinhalaEdApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => ThemeProvider()..initializeTheme(),
        ),
        ChangeNotifierProvider(
          create: (_) => AuthController(),
        ),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, child) {
          return MaterialApp(
            title: 'Sinhala Ed Assistant',
            debugShowCheckedModeBanner: false,

            // Theme configuration
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: themeProvider.materialThemeMode,

            // Navigation configuration
            initialRoute: AppRoutes.splash,
            navigatorKey: NavigationService.navigatorKey,
            routes: AppPages.routes,
            onGenerateRoute: RouteGenerator.generateRoute,
          );
        },
      ),
    );
  }
}
