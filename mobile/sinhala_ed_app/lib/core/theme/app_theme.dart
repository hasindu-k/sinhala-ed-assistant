import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_text_styles.dart';

/// Centralized theme configuration for the Sinhala Ed Assistant app
class AppTheme {
  // Private constructor to prevent instantiation
  AppTheme._();

  /// Light theme configuration
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: _lightColorScheme,
      fontFamily: AppTextStyles.fontFamily,

      // App Bar Theme
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 2,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: AppTextStyles.appBarTitle.copyWith(
          color: AppColors.onSurfaceLight,
        ),
      ),

      // Text Theme
      textTheme: AppTextStyles.getTextTheme(isDark: false),

      // Elevated Button Theme
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 2,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Text Button Theme
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Card Theme
      cardTheme: const CardThemeData(
        elevation: 2,
        margin: EdgeInsets.all(8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
      ),

      // Dialog Theme
      dialogTheme: DialogThemeData(
        elevation: 8,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
        ),
        titleTextStyle: AppTextStyles.headlineMedium.copyWith(
          color: AppColors.onSurfaceLight,
        ),
        contentTextStyle: AppTextStyles.bodyLarge.copyWith(
          color: AppColors.onSurfaceLight,
        ),
      ),

      // Input Decoration Theme
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          borderSide: BorderSide(color: AppColors.primaryBlue, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          borderSide: BorderSide(color: AppColors.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          borderSide: BorderSide(color: AppColors.error, width: 2),
        ),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    );
  }

  /// Dark theme configuration
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: _darkColorScheme,
      fontFamily: AppTextStyles.fontFamily,

      // App Bar Theme
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 2,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: AppTextStyles.appBarTitle.copyWith(
          color: AppColors.onSurfaceDark,
        ),
      ),

      // Text Theme
      textTheme: AppTextStyles.getTextTheme(isDark: true),

      // Elevated Button Theme
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 2,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Text Button Theme
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Card Theme
      cardTheme: const CardThemeData(
        elevation: 2,
        margin: EdgeInsets.all(8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
      ),

      // Dialog Theme
      dialogTheme: DialogThemeData(
        elevation: 8,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
        ),
        titleTextStyle: AppTextStyles.headlineMedium.copyWith(
          color: AppColors.onSurfaceDark,
        ),
        contentTextStyle: AppTextStyles.bodyLarge.copyWith(
          color: AppColors.onSurfaceDark,
        ),
      ),

      // Input Decoration Theme
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          borderSide: BorderSide(color: AppColors.primaryBlueLight, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          borderSide: BorderSide(color: AppColors.errorLight),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(8)),
          borderSide: BorderSide(color: AppColors.errorLight, width: 2),
        ),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    );
  }

  // Color schemes
  static const ColorScheme _lightColorScheme = ColorScheme(
    brightness: Brightness.light,
    primary: AppColors.primaryBlue,
    onPrimary: AppColors.white,
    primaryContainer: AppColors.primaryBlueContainer,
    onPrimaryContainer: AppColors.primaryBlueDark,
    secondary: AppColors.secondaryGreen,
    onSecondary: AppColors.white,
    secondaryContainer: AppColors.secondaryGreenContainer,
    onSecondaryContainer: AppColors.secondaryGreenDark,
    tertiary: AppColors.tertiaryOrange,
    onTertiary: AppColors.white,
    tertiaryContainer: AppColors.tertiaryOrangeContainer,
    onTertiaryContainer: AppColors.tertiaryOrangeDark,
    error: AppColors.error,
    onError: AppColors.white,
    errorContainer: AppColors.errorContainer,
    onErrorContainer: AppColors.errorDark,
    surface: AppColors.surfaceLight,
    onSurface: AppColors.onSurfaceLight,
    surfaceContainerHighest: AppColors.surfaceContainerLight,
    onSurfaceVariant: AppColors.onSurfaceVariantLight,
    outline: AppColors.outlineLight,
    outlineVariant: AppColors.surfaceContainerLight,
    shadow: AppColors.black,
    scrim: AppColors.black,
    inverseSurface: AppColors.inverseSurfaceLight,
    onInverseSurface: AppColors.onInverseSurfaceLight,
    inversePrimary: AppColors.primaryBlueLight,
    surfaceTint: AppColors.primaryBlue,
  );

  static const ColorScheme _darkColorScheme = ColorScheme(
    brightness: Brightness.dark,
    primary: AppColors.primaryBlueLight,
    onPrimary: AppColors.primaryBlueDark,
    primaryContainer: AppColors.primaryBlueContainerDark,
    onPrimaryContainer: AppColors.primaryBlueContainer,
    secondary: AppColors.secondaryGreenLight,
    onSecondary: AppColors.secondaryGreenDark,
    secondaryContainer: AppColors.secondaryGreenContainerDark,
    onSecondaryContainer: AppColors.secondaryGreenContainer,
    tertiary: AppColors.tertiaryOrangeLight,
    onTertiary: AppColors.tertiaryOrangeDark,
    tertiaryContainer: AppColors.tertiaryOrangeContainerDark,
    onTertiaryContainer: AppColors.tertiaryOrangeContainer,
    error: AppColors.errorLight,
    onError: AppColors.errorDark,
    errorContainer: AppColors.errorContainerDark,
    onErrorContainer: AppColors.errorContainer,
    surface: AppColors.surfaceDark,
    onSurface: AppColors.onSurfaceDark,
    surfaceContainerHighest: AppColors.surfaceContainerDark,
    onSurfaceVariant: AppColors.onSurfaceVariantDark,
    outline: AppColors.outlineDark,
    outlineVariant: AppColors.surfaceContainerDark,
    shadow: AppColors.black,
    scrim: AppColors.black,
    inverseSurface: AppColors.inverseSurfaceDark,
    onInverseSurface: AppColors.onInverseSurfaceDark,
    inversePrimary: AppColors.primaryBlue,
    surfaceTint: AppColors.primaryBlueLight,
  );
}
