import 'package:flutter/material.dart';
import '../pages/home_page.dart';
import '../pages/login_page.dart';
import '../pages/splash_page.dart';
import 'app_routes.dart';

class AppPages {
  static Map<String, WidgetBuilder> routes = {
    AppRoutes.splash: (_) => SplashPage(),
    AppRoutes.home: (_) => HomePage(),
    AppRoutes.login: (_) => LoginPage(),
  };
}
