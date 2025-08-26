import 'package:flutter/material.dart';

class AppDialogs {
  static Future<bool> confirm(
    BuildContext context, {
    required String title,
    required String message,
    String cancelText = 'Cancel',
    String okText = 'OK',
    bool okIsDestructive = false,
    bool barrierDismissible = true,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(cancelText),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            style: okIsDestructive
                ? TextButton.styleFrom(
                    foregroundColor: Theme.of(context).colorScheme.error,
                  )
                : null,
            child: Text(okText),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  static Future<bool> confirmExit(BuildContext context) {
    return confirm(
      context,
      title: 'Exit App',
      message: 'Are you sure you want to exit?',
      okText: 'Exit',
      okIsDestructive: true,
      barrierDismissible: false,
    );
  }
}
