import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_text_styles.dart';

/// Centralized theme configuration for the SinhalaLearn app
class AppTheme {
  AppTheme._(); // prevent instantiation

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
          color: AppColors.black,
        ),
      ),

      // Text Theme
      textTheme: AppTextStyles.getTextTheme(isDark: false),

      // Elevated Button Theme
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryBlue,
          foregroundColor: AppColors.white,
          elevation: 2,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Text Button Theme
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryBlue,
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
          color: AppColors.black,
        ),
        contentTextStyle: AppTextStyles.bodyLarge.copyWith(
          color: AppColors.greyDark,
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
          color: AppColors.white,
        ),
      ),

      // Text Theme
      textTheme: AppTextStyles.getTextTheme(isDark: true),

      // Elevated Button Theme
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryBlueLight,
          foregroundColor: AppColors.black,
          elevation: 2,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: AppTextStyles.buttonText,
        ),
      ),

      // Text Button Theme
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryBlueLight,
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
          color: AppColors.white,
        ),
        contentTextStyle: AppTextStyles.bodyLarge.copyWith(
          color: AppColors.greyLight,
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
    tertiary: AppColors.sinhalaGold,
    onTertiary: AppColors.black,
    tertiaryContainer: AppColors.sinhalaGoldLight,
    onTertiaryContainer: AppColors.sinhalaGoldDark,
    error: AppColors.error,
    onError: AppColors.white,
    errorContainer: AppColors.greyLight,
    onErrorContainer: AppColors.error,
    surface: AppColors.backgroundLight,
    onSurface: AppColors.black,
    surfaceContainerHighest: AppColors.greyLight,
    onSurfaceVariant: AppColors.greyDark,
    outline: AppColors.grey,
    outlineVariant: AppColors.greyLight,
    shadow: AppColors.black,
    scrim: AppColors.black,
    inverseSurface: AppColors.greyDark,
    onInverseSurface: AppColors.white,
    inversePrimary: AppColors.primaryBlueLight,
    surfaceTint: AppColors.primaryBlue,
  );

  static const ColorScheme _darkColorScheme = ColorScheme(
    brightness: Brightness.dark,
    primary: AppColors.primaryBlueLight,
    onPrimary: AppColors.black,
    primaryContainer: AppColors.primaryBlueDark,
    onPrimaryContainer: AppColors.primaryBlueContainer,
    secondary: AppColors.secondaryGreenLight,
    onSecondary: AppColors.black,
    secondaryContainer: AppColors.secondaryGreenDark,
    onSecondaryContainer: AppColors.secondaryGreenContainer,
    tertiary: AppColors.sinhalaGoldLight,
    onTertiary: AppColors.black,
    tertiaryContainer: AppColors.sinhalaGoldDark,
    onTertiaryContainer: AppColors.sinhalaGold,
    error: AppColors.error,
    onError: AppColors.white,
    errorContainer: AppColors.greyDark,
    onErrorContainer: AppColors.error,
    surface: AppColors.backgroundDark,
    onSurface: AppColors.white,
    surfaceContainerHighest: AppColors.greyDark,
    onSurfaceVariant: AppColors.grey,
    outline: AppColors.grey,
    outlineVariant: AppColors.greyDark,
    shadow: AppColors.black,
    scrim: AppColors.black,
    inverseSurface: AppColors.white,
    onInverseSurface: AppColors.black,
    inversePrimary: AppColors.primaryBlue,
    surfaceTint: AppColors.primaryBlueLight,
  );
}
