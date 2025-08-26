import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/providers/theme_provider.dart';
import '../../core/theme/theme.dart';

class ThemeSettingsPage extends StatelessWidget {
  const ThemeSettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Theme Settings'), elevation: 0),
      body: SafeArea(
        child: Consumer<ThemeProvider>(
          builder: (context, themeProvider, child) {
            return Column(
              children: [
                const SizedBox(height: 16),
                Card(
                  margin: const EdgeInsets.all(16),
                  shape: RoundedRectangleBorder(
                    borderRadius: ThemeUtils.getCardBorderRadius(),
                  ),
                  elevation: ThemeUtils.getCardElevation(context),
                  child: Padding(
                    padding: ThemeUtils.getContentPadding(),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Choose Theme',
                          style: AppTextStyles.titleLarge.copyWith(
                            fontWeight: FontWeight.bold,
                            color: ThemeUtils.getTextColor(context),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Select your preferred theme mode',
                          style: AppTextStyles.bodyMedium.copyWith(
                            color: ThemeUtils.getSecondaryTextColor(context),
                          ),
                        ),
                        const SizedBox(height: 20),
                        ...AppThemeMode.values.map((mode) {
                          return _buildThemeOption(
                            context,
                            mode,
                            themeProvider.themeMode == mode,
                            (selected) {
                              if (selected) {
                                themeProvider.setThemeMode(mode);
                              }
                            },
                          );
                        }),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                _buildPreviewCard(context),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildThemeOption(
    BuildContext context,
    AppThemeMode mode,
    bool isSelected,
    Function(bool) onChanged,
  ) {
    String title;
    String subtitle;
    IconData icon;

    switch (mode) {
      case AppThemeMode.light:
        title = 'Light';
        subtitle = 'Always use light theme';
        icon = Icons.light_mode;
        break;
      case AppThemeMode.dark:
        title = 'Dark';
        subtitle = 'Always use dark theme';
        icon = Icons.dark_mode;
        break;
      case AppThemeMode.system:
        title = 'System default';
        subtitle = 'Follow system theme settings';
        icon = Icons.brightness_auto;
        break;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => onChanged(true),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
          child: Row(
            children: [
              // Custom radio circle
              Container(
                width: 20,
                height: 20,
                margin: const EdgeInsets.only(right: 12),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isSelected
                        ? ThemeUtils.getPrimaryColor(context)
                        : ThemeUtils.getSecondaryTextColor(context),
                    width: 2,
                  ),
                ),
                child: isSelected
                    ? Center(
                        child: Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: ThemeUtils.getPrimaryColor(context),
                          ),
                        ),
                      )
                    : null,
              ),

              // Icon
              Icon(
                icon,
                size: 20,
                color: isSelected
                    ? ThemeUtils.getPrimaryColor(context)
                    : ThemeUtils.getSecondaryTextColor(context),
              ),
              const SizedBox(width: 12),

              // Texts
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppTextStyles.bodyLarge.copyWith(
                        fontWeight:
                            isSelected ? FontWeight.w600 : FontWeight.normal,
                        color: ThemeUtils.getTextColor(context),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: AppTextStyles.bodyMedium.copyWith(
                        color: ThemeUtils.getSecondaryTextColor(context),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPreviewCard(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      shape: RoundedRectangleBorder(
          borderRadius: ThemeUtils.getCardBorderRadius()),
      elevation: ThemeUtils.getCardElevation(context),
      child: Padding(
        padding: ThemeUtils.getContentPadding(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.preview,
                  color: ThemeUtils.getPrimaryColor(context),
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Theme Preview',
                  style: AppTextStyles.titleMedium.copyWith(
                    fontWeight: FontWeight.bold,
                    color: ThemeUtils.getTextColor(context),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: ThemeUtils.getContentPadding(),
              decoration: BoxDecoration(
                color: ThemeUtils.getSurfaceColor(context),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: ThemeUtils.getSecondaryTextColor(context)
                      .withValues(alpha: 0.2),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Sample Content',
                    style: AppTextStyles.titleSmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: ThemeUtils.getTextColor(context),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'This is how your content will look with the current theme.',
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: ThemeUtils.getSecondaryTextColor(context),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.check_circle,
                        size: 16,
                        color: ThemeUtils.getPrimaryColor(context),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Theme applied',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: ThemeUtils.getPrimaryColor(context),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
