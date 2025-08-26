# Theme System Documentation

This document explains the theme system organization for the Sinhala Ed Assistant app.

## Overview

The theme logic has been separated into multiple files for better organization, maintainability, and reusability. The theme system supports both light and dark modes with automatic system theme detection.

## File Structure

```
lib/core/theme/
├── theme.dart              # Main export file
├── app_theme.dart          # Theme configurations
├── app_colors.dart         # Color constants
├── app_text_styles.dart    # Text style definitions
└── theme_utils.dart        # Theme utility functions
```

## Files Description

### 1. `theme.dart`

Main export file that re-exports all theme-related classes. Import this file to access all theme functionality:

```dart
import 'package:sinhala_ed_app/core/theme/theme.dart';
```

### 2. `app_theme.dart`

Contains the main `AppTheme` class with:

- `lightTheme`: Complete light theme configuration
- `darkTheme`: Complete dark theme configuration
- Color schemes for both themes
- Component themes (AppBar, Buttons, Cards, Dialogs, etc.)

### 3. `app_colors.dart`

Defines all color constants used throughout the app:

- Primary colors (blue variations)
- Secondary colors (green variations)
- Tertiary colors (orange variations)
- Error colors
- Neutral colors for light/dark themes
- Custom brand colors
- Status colors (success, warning, info)

### 4. `app_text_styles.dart`

Contains text style definitions:

- Display styles (large, medium, small)
- Headline styles
- Title styles
- Body text styles
- Label styles
- Custom app-specific styles
- Helper method to generate theme-aware text styles

### 5. `theme_utils.dart`

Utility functions for theme-related operations:

- Theme detection (light/dark mode)
- Color getters based on current theme
- Dimension helpers (padding, border radius)
- Context-aware styling helpers

## Usage Examples

### Basic Theme Usage

```dart
// In main app file
class SinhalaEdApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system, // Follows system preference
      // ... other properties
    );
  }
}
```

### Using Colors

```dart
// Direct color usage
Container(
  color: AppColors.primaryBlue,
  child: Text(
    'Hello',
    style: TextStyle(color: AppColors.white),
  ),
)

// Theme-aware color usage
Container(
  color: Theme.of(context).colorScheme.primary,
  child: Text(
    'Hello',
    style: TextStyle(
      color: Theme.of(context).colorScheme.onPrimary,
    ),
  ),
)
```

### Using Text Styles

```dart
// Direct text style usage
Text(
  'Title',
  style: AppTextStyles.headlineLarge,
)

// Theme-aware text style usage
Text(
  'Title',
  style: Theme.of(context).textTheme.headlineLarge,
)
```

### Using Theme Utils

```dart
// Check if dark mode
bool isDark = ThemeUtils.isDarkMode(context);

// Get theme-appropriate colors
Color textColor = ThemeUtils.getTextColor(context);
Color errorColor = ThemeUtils.getErrorColor(context);

// Use predefined dimensions
Container(
  padding: ThemeUtils.getContentPadding(),
  decoration: BoxDecoration(
    borderRadius: ThemeUtils.getCardBorderRadius(),
  ),
  child: Text('Content'),
)
```

### Creating Theme-Aware Widgets

```dart
class ThemedCard extends StatelessWidget {
  final Widget child;

  const ThemedCard({Key? key, required this.child}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: ThemeUtils.getCardElevation(context),
      shape: RoundedRectangleBorder(
        borderRadius: ThemeUtils.getCardBorderRadius(),
      ),
      child: Padding(
        padding: ThemeUtils.getContentPadding(),
        child: child,
      ),
    );
  }
}
```

## Customization

### Adding New Colors

1. Add color constants to `AppColors` class
2. Update color schemes in `AppTheme` if needed
3. Add theme utility methods if required

### Adding New Text Styles

1. Define styles in `AppTextStyles` class
2. Update `getTextTheme()` method to include new styles
3. Use consistent naming conventions

### Modifying Themes

1. Update component themes in `AppTheme.lightTheme` and `AppTheme.darkTheme`
2. Ensure both themes are updated consistently
3. Test in both light and dark modes

## Best Practices

1. **Use theme-aware colors**: Prefer `Theme.of(context).colorScheme.primary` over `AppColors.primaryBlue`
2. **Consistent naming**: Follow Material Design naming conventions
3. **Test both themes**: Always test your UI in both light and dark modes
4. **Use semantic colors**: Use appropriate semantic colors (error, success, warning)
5. **Responsive design**: Consider different screen sizes when defining dimensions
6. **Accessibility**: Ensure sufficient contrast ratios for text and backgrounds

## Theme Switching

The app automatically follows the system theme by default. To implement manual theme switching:

```dart
// In your app state management
enum ThemeMode { light, dark, system }

// To change theme
ThemeMode currentTheme = ThemeMode.light; // or dark, system

MaterialApp(
  theme: AppTheme.lightTheme,
  darkTheme: AppTheme.darkTheme,
  themeMode: currentTheme,
  // ...
)
```

## Testing Themes

Always test your UI components in both light and dark themes:

```dart
// In tests
testWidgets('Widget looks good in light theme', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.lightTheme,
      home: YourWidget(),
    ),
  );
  // Test assertions
});

testWidgets('Widget looks good in dark theme', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.darkTheme,
      home: YourWidget(),
    ),
  );
  // Test assertions
});
```
