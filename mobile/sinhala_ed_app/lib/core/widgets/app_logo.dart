import 'package:flutter/material.dart';

class AppLogo extends StatelessWidget {
  final double height;
  final EdgeInsetsGeometry padding;
  final String assetPath;

  const AppLogo({
    super.key,
    this.height = 100,
    this.padding = const EdgeInsets.only(top: 24, bottom: 24),
    this.assetPath = 'assets/images/logo.png',
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Image.asset(assetPath, height: height),
    );
  }
}
