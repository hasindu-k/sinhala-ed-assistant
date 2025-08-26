import 'package:flutter/material.dart';

/// Supported application languages
enum AppLanguage { si, en }

/// User-friendly labels
String langLabel(AppLanguage l) {
  switch (l) {
    case AppLanguage.si:
      return 'සිංහල (Sinhala)';
    case AppLanguage.en:
      return 'English';
  }
}

/// Icons for each language
IconData langIcon(AppLanguage l) {
  switch (l) {
    case AppLanguage.si:
      return Icons.translate;
    case AppLanguage.en:
      return Icons.language;
  }
}
