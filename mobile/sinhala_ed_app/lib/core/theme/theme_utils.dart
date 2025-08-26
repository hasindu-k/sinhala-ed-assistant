import 'package:flutter/material.dart';
import 'package:sinhala_ed_app/core/theme/theme.dart';

/// Utility class for theme-related helper functions
class ThemeUtils {
  // Private constructor to prevent instantiation
  ThemeUtils._();

  /// Returns true if the current theme is dark mode
  static bool isDarkMode(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark;
  }

  /// Returns the primary color based on the current theme
  static Color getPrimaryColor(BuildContext context) {
    return Theme.of(context).colorScheme.primary;
  }

  /// Returns the surface color based on the current theme
  static Color getSurfaceColor(BuildContext context) {
    return Theme.of(context).colorScheme.surface;
  }

  /// Returns the on-surface color based on the current theme
  static Color getOnSurfaceColor(BuildContext context) {
    return Theme.of(context).colorScheme.onSurface;
  }

  /// Returns the appropriate text color for the current theme
  static Color getTextColor(BuildContext context) {
    return Theme.of(context).colorScheme.onSurface;
  }

  /// Returns the appropriate secondary text color for the current theme
  static Color getSecondaryTextColor(BuildContext context) {
    return Theme.of(context).colorScheme.onSurfaceVariant;
  }

  /// Returns the appropriate error color for the current theme
  static Color getErrorColor(BuildContext context) {
    return Theme.of(context).colorScheme.error;
  }

  /// Returns the appropriate success color for the current theme
  static Color getSuccessColor(BuildContext context) {
    return isDarkMode(context)
        ? const Color(0xFF4CAF50)
        : const Color(0xFF2E7D32);
  }

  /// Returns the appropriate warning color for the current theme
  static Color getWarningColor(BuildContext context) {
    return isDarkMode(context)
        ? const Color(0xFFFFC107)
        : const Color(0xFFF57C00);
  }

  /// Returns the appropriate card elevation for the current theme
  static double getCardElevation(BuildContext context) {
    return isDarkMode(context) ? 4.0 : 2.0;
  }

  /// Returns the appropriate border radius for cards and buttons
  static BorderRadius getCardBorderRadius() {
    return BorderRadius.circular(12.0);
  }

  /// Returns the appropriate border radius for inputs
  static BorderRadius getInputBorderRadius() {
    return BorderRadius.circular(8.0);
  }

  /// Returns appropriate padding for content
  static EdgeInsets getContentPadding() {
    return const EdgeInsets.all(16.0);
  }

  /// Returns appropriate padding for buttons
  static EdgeInsets getButtonPadding() {
    return const EdgeInsets.symmetric(horizontal: 24.0, vertical: 12.0);
  }

  /// Returns appropriate small padding
  static EdgeInsets getSmallPadding() {
    return const EdgeInsets.all(8.0);
  }

  /// Returns appropriate large padding
  static EdgeInsets getLargePadding() {
    return const EdgeInsets.all(24.0);
  }

  static Color getSplashBackgroundColor(BuildContext context) {
    return isDarkMode(context) ? AppColors.splashDark : AppColors.splashLight;
  }
}
