import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:SinhalaLearn/presentation/routes/route_generator.dart';
import 'package:SinhalaLearn/presentation/routes/app_routes.dart';
import 'package:SinhalaLearn/presentation/pages/splash_page.dart';
import 'package:SinhalaLearn/presentation/pages/login_page.dart';
import 'package:SinhalaLearn/presentation/pages/home_page.dart';

void main() {
  group('RouteGenerator Tests', () {
    testWidgets('Splash route returns SplashPage', (WidgetTester tester) async {
      final route = RouteGenerator.generateRoute(
        const RouteSettings(name: AppRoutes.splash),
      );

      await tester.pumpWidget(MaterialApp(onGenerateRoute: (_) => route));

      expect(find.byType(SplashPage), findsOneWidget);
    });

    testWidgets('Login route returns LoginPage', (WidgetTester tester) async {
      final route = RouteGenerator.generateRoute(
        const RouteSettings(name: AppRoutes.login),
      );

      await tester.pumpWidget(MaterialApp(onGenerateRoute: (_) => route));

      expect(find.byType(LoginPage), findsOneWidget);
    });

    testWidgets('Home route returns HomePage', (WidgetTester tester) async {
      final route = RouteGenerator.generateRoute(
        const RouteSettings(name: AppRoutes.home),
      );

      await tester.pumpWidget(MaterialApp(onGenerateRoute: (_) => route));

      expect(find.byType(HomePage), findsOneWidget);
    });

    testWidgets('Unknown route shows error page', (WidgetTester tester) async {
      final route = RouteGenerator.generateRoute(
        const RouteSettings(name: '/unknown'),
      );

      await tester.pumpWidget(MaterialApp(onGenerateRoute: (_) => route));

      expect(find.text('Route not found: /unknown'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(find.byType(ElevatedButton), findsOneWidget);
    });
  });
}
