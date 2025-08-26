import 'package:flutter/material.dart';
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
      initialRoute: AppRoutes.login,
      navigatorKey: NavigationService.navigatorKey,
      routes: AppPages.routes,
      onGenerateRoute: RouteGenerator.generateRoute,
    );
  }
}
