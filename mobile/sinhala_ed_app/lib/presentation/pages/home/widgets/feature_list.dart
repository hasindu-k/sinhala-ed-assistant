import 'package:flutter/material.dart';
import '../../../../data/models/feature_item.dart';
import 'feature_card.dart';

class FeatureList extends StatelessWidget {
  final List<FeatureItem> features;

  const FeatureList({super.key, required this.features});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: features
          .map(
            (feature) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 6.0),
              child: FeatureCard(
                icon: feature.icon,
                title: feature.title,
                bullets: feature.bullets,
                onTap: feature.onTap,
              ),
            ),
          )
          .toList(),
    );
  }
}
