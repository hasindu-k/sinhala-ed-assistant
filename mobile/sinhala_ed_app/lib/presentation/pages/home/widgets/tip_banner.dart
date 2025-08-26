// lib/presentation/pages/home/widgets/tip_banner.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/theme.dart';

class TipBanner extends StatelessWidget {
  final IconData icon;
  final String text;

  const TipBanner({super.key, required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: ThemeUtils.getContentPadding(),
      decoration: BoxDecoration(
        color: ThemeUtils.getSurfaceColor(context),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color:
              ThemeUtils.getSecondaryTextColor(context).withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: ThemeUtils.getPrimaryColor(context)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: AppTextStyles.bodyMedium.copyWith(
                color: ThemeUtils.getTextColor(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
