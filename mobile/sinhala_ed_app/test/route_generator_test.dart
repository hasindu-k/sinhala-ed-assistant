import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sinhala_ed_app/presentation/routes/route_generator.dart';
import 'package:sinhala_ed_app/presentation/routes/app_routes.dart';
import 'package:sinhala_ed_app/presentation/routes/navigation_service.dart';
import 'package:sinhala_ed_app/presentation/pages/splash_page.dart';
import 'package:sinhala_ed_app/presentation/pages/login_page.dart';
import 'package:sinhala_ed_app/presentation/pages/home_page.dart';

void main() {
  group('RouteGenerator Tests', () {
    testWidgets('Splash route returns SplashPage', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          navigatorKey: NavigationService.navigatorKey,
          onGenerateRoute: RouteGenerator.generateRoute,
          initialRoute: AppRoutes.splash,
        ),
      );

      expect(find.byType(SplashPage), findsOneWidget);

      // Wait for the timer to complete and navigation to happen
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // After navigation, we should be on the home page
      expect(find.byType(HomePage), findsOneWidget);
    });

    testWidgets('Login route returns LoginPage', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          navigatorKey: NavigationService.navigatorKey,
          onGenerateRoute: RouteGenerator.generateRoute,
          initialRoute: AppRoutes.login,
        ),
      );

      expect(find.byType(LoginPage), findsOneWidget);
    });

    testWidgets('Home route returns HomePage', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          navigatorKey: NavigationService.navigatorKey,
          onGenerateRoute: RouteGenerator.generateRoute,
          initialRoute: AppRoutes.home,
        ),
      );

      expect(find.byType(HomePage), findsOneWidget);
    });

    testWidgets('Unknown route shows error page', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          navigatorKey: NavigationService.navigatorKey,
          onGenerateRoute: RouteGenerator.generateRoute,
          initialRoute: '/unknown',
        ),
      );

      expect(find.text('Route not found: /unknown'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(find.byType(ElevatedButton), findsOneWidget);
    });
  });
}
