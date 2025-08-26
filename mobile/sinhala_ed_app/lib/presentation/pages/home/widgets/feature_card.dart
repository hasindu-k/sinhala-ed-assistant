// lib/presentation/pages/home/widgets/feature_card.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/theme.dart';

class FeatureCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final List<String> bullets;
  final VoidCallback? onTap;

  const FeatureCard({
    super.key,
    required this.icon,
    required this.title,
    required this.bullets,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: ThemeUtils.getCardElevation(context),
      shape: RoundedRectangleBorder(
        borderRadius: ThemeUtils.getCardBorderRadius(),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap ??
            () => ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('$title — opening soon')),
                ),
        child: Padding(
          padding: ThemeUtils.getContentPadding(),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 28, color: ThemeUtils.getPrimaryColor(context)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title
                    Text(
                      title,
                      style: AppTextStyles.titleMedium.copyWith(
                        fontWeight: FontWeight.w700,
                        color: ThemeUtils.getTextColor(context),
                      ),
                    ),
                    const SizedBox(height: 8),
                    // Bullets (no scrolling)
                    ...bullets.map(
                      (b) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('•  '),
                            Expanded(
                              child: Text(
                                b,
                                style: AppTextStyles.bodyMedium.copyWith(
                                  color:
                                      ThemeUtils.getSecondaryTextColor(context),
                                ),
                              ),
                            ),
                          ],
                        ),
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
}
