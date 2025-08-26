import 'package:flutter/material.dart';

/// Brand color constants for SinhalaLearn app
class AppColors {
  AppColors._(); // prevent instantiation

  // Primary Brand Colors (Blue tones from logo)
  static const Color primaryBlue = Color(0xFF1976D2); // Medium Blue
  static const Color primaryBlueDark = Color(0xFF0D47A1); // Deep Blue
  static const Color primaryBlueLight = Color(0xFF64B5F6); // Accent Blue
  static const Color primaryBlueContainer = Color(0xFFBBDEFB);

  // Secondary Brand Colors (Green pixel element)
  static const Color secondaryGreen = Color(0xFF388E3C);
  static const Color secondaryGreenDark = Color(0xFF1B5E20);
  static const Color secondaryGreenLight = Color(0xFF81C784);
  static const Color secondaryGreenContainer = Color(0xFFC8E6C9);

  // Accent Brand Colors (Sinhala "අ")
  static const Color sinhalaGold = Color(0xFFFFD700); // Bright Gold
  static const Color sinhalaGoldDark = Color(0xFFFFB300); // Rich Gold
  static const Color sinhalaGoldLight = Color(0xFFFFE082); // Soft Yellow

  // Neutral Colors
  static const Color white = Color(0xFFFFFFFF);
  static const Color black = Color(0xFF000000);
  static const Color greyLight = Color(0xFFF5F5F5);
  static const Color grey = Color(0xFF9E9E9E);
  static const Color greyDark = Color(0xFF424242);

  // Backgrounds
  static const Color backgroundLight = Color(0xFFF9FAFB);
  static const Color backgroundDark = Color(0xFF121212);

  // Card and Surfaces
  static const Color cardLight = Color(0xFFFFFFFF);
  static const Color cardDark = Color(0xFF1E1E1E);

  // Status Colors
  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFFC107);
  static const Color error = Color(0xFFD32F2F);
  static const Color info = Color(0xFF2196F3);

  static const Color splashLight = Color(0xFFF3F4F6);
  static const Color splashDark = Color(0xFFA6A6A6);
}
