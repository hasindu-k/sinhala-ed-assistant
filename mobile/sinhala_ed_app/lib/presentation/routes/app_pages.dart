import 'package:flutter/material.dart';
import '../pages/home/home_page.dart';
import '../../features/auth/view/login_page.dart';
import '../../features/auth/view/register_page.dart';
import '../pages/splash_page.dart';
import '../pages/profile_page.dart';
import 'app_routes.dart';

class AppPages {
  static Map<String, WidgetBuilder> routes = {
    AppRoutes.splash: (_) => SplashPage(),
    AppRoutes.home: (_) => HomePage(),
    AppRoutes.login: (_) => LoginPage(),
    AppRoutes.profile: (_) => ProfilePage(),
    AppRoutes.register: (_) => RegisterPage(),
  };
}
