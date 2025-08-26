import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/providers/theme_provider.dart';
import '../../core/utils/dialogs.dart';
import '../../core/theme/theme.dart';
import '../../core/i18n/app_language.dart';

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile'), elevation: 0),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: ThemeUtils.getContentPadding(),
          child: Column(
            children: [
              _buildProfileHeader(context),
              const SizedBox(height: 24),
              _buildProfileInfo(context),
              const SizedBox(height: 24),
              _buildSettingsSection(context),
              const SizedBox(height: 24),
              _buildActionButtons(context),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProfileHeader(BuildContext context) {
    return Card(
      elevation: 0, // no shadow
      color: Colors.transparent, // no background
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.zero),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            CircleAvatar(
              radius: 50,
              backgroundColor: ThemeUtils.getPrimaryColor(context),
              child: Icon(
                Icons.person,
                size: 50,
                color: Theme.of(context).colorScheme.onPrimary,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'User Name',
              textAlign: TextAlign.center,
              style: AppTextStyles.headlineSmall.copyWith(
                fontWeight: FontWeight.bold,
                color: ThemeUtils.getTextColor(context),
              ),
            ),
            const SizedBox(height: 4),
            SelectableText(
              'user@example.com',
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyMedium.copyWith(
                color: ThemeUtils.getSecondaryTextColor(context),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileInfo(BuildContext context) {
    return Card(
      shape: RoundedRectangleBorder(
          borderRadius: ThemeUtils.getCardBorderRadius()),
      elevation: ThemeUtils.getCardElevation(context),
      child: Padding(
        padding: ThemeUtils.getContentPadding(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Profile Information',
              style: AppTextStyles.titleLarge.copyWith(
                fontWeight: FontWeight.bold,
                color: ThemeUtils.getTextColor(context),
              ),
            ),
            const SizedBox(height: 16),
            _buildInfoRow(context, 'Full Name', 'John Doe'),
            _buildInfoRow(context, 'Email', 'user@example.com'),
            _buildInfoRow(context, 'Phone', '+94 12 345 6789'),
            _buildInfoRow(context, 'Grade Level', 'Grade 10'),
            _buildInfoRow(context, 'School', 'Example School'),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w600,
                color: ThemeUtils.getSecondaryTextColor(context),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                color: ThemeUtils.getTextColor(context),
              ),
              overflow: TextOverflow.ellipsis,
              maxLines: 2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsSection(BuildContext context) {
    final tiles = [
      _buildSettingsTile(
        context,
        icon: Icons.language,
        title: 'Language',
        subtitle: 'English',
        onTap: () => _showLanguageDialog(context),
      ),
      _buildSettingsTile(
        context,
        icon: Icons.notifications,
        title: 'Notifications',
        subtitle: 'Enabled',
        onTap: () => _comingSoon(context, 'Notification settings'),
      ),
      _buildSettingsTile(
        context,
        icon: Icons.dark_mode,
        title: 'Theme',
        subtitle: context.watch<ThemeProvider>().themeModeDisplayName,
        onTap: () => _showThemeModeDialog(context),
      ),
      _buildSettingsTile(
        context,
        icon: Icons.privacy_tip,
        title: 'Privacy',
        subtitle: 'Manage your privacy',
        onTap: () => _comingSoon(context, 'Privacy settings'),
      ),
    ];

    return Card(
      shape: RoundedRectangleBorder(
          borderRadius: ThemeUtils.getCardBorderRadius()),
      elevation: ThemeUtils.getCardElevation(context),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: ListTile.divideTiles(
            context: context,
            tiles: tiles,
          ).toList(),
        ),
      ),
    );
  }

  Widget _buildSettingsTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: ThemeUtils.getPrimaryColor(context)),
      title: Text(
        title,
        style: AppTextStyles.bodyLarge
            .copyWith(color: ThemeUtils.getTextColor(context)),
      ),
      subtitle: Text(
        subtitle,
        style: AppTextStyles.bodyMedium.copyWith(
          color: ThemeUtils.getSecondaryTextColor(context),
        ),
      ),
      trailing: Icon(
        Icons.chevron_right,
        color: ThemeUtils.getSecondaryTextColor(context),
      ),
      visualDensity: VisualDensity.compact,
      onTap: onTap,
    );
  }

  Widget _buildActionButtons(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => _comingSoon(context, 'Edit profile'),
            icon: const Icon(Icons.edit),
            label: Text('Edit Profile', style: AppTextStyles.buttonText),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () async {
              final ok = await AppDialogs.confirm(
                context,
                title: 'Logout',
                message: 'Are you sure you want to logout?',
                okText: 'Logout',
                okIsDestructive: true,
              );
              if (ok) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                      content: Text('Logout functionality coming soon!')),
                );
              }
            },
            icon: const Icon(Icons.logout),
            label: Text('Logout', style: AppTextStyles.buttonText),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 12),
              foregroundColor: Theme.of(context).colorScheme.error,
              side: BorderSide(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ),
      ],
    );
  }

  void _comingSoon(BuildContext context, String what) {
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('$what coming soon!')));
  }
}

void _showThemeModeDialog(BuildContext context) async {
  final themeProvider = context.read<ThemeProvider>();
  final current = themeProvider.themeMode;

  final selected = await AppDialogs.chooseOption<AppThemeMode>(
    context,
    title: 'Choose Theme',
    options: AppThemeMode.values,
    selected: current,
    getLabel: (mode) {
      switch (mode) {
        case AppThemeMode.light:
          return 'Light';
        case AppThemeMode.dark:
          return 'Dark';
        case AppThemeMode.system:
          return 'System Default';
      }
    },
    getIcon: (mode) {
      switch (mode) {
        case AppThemeMode.light:
          return Icons.light_mode;
        case AppThemeMode.dark:
          return Icons.dark_mode;
        case AppThemeMode.system:
          return Icons.brightness_auto;
      }
    },
  );

  if (selected != null) {
    themeProvider.setThemeMode(selected);
  }
}

Future<void> _showLanguageDialog(BuildContext context) async {
  final selected = await AppDialogs.chooseOption<AppLanguage>(
    context,
    title: 'Choose Language',
    options: AppLanguage.values,
    selected: null, // later: pass your current language from provider
    getLabel: langLabel,
    getIcon: langIcon,
  );

  if (!context.mounted) return;

  if (selected != null) {
    // For now, just show "coming soon"
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${langLabel(selected)} support coming soon!')),
    );

    // TODO: later -> context.read<LanguageProvider>().setLanguage(selected);
  }
}
