import 'package:flutter/material.dart';

class AppDialogs {
  /// Simple confirmation dialog (Yes/No)
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

  /// Generic option picker dialog
  static Future<T?> chooseOption<T>(
    BuildContext context, {
    required String title,
    required List<T> options,
    required String Function(T) getLabel,
    IconData Function(T)? getIcon,
    T? selected,
    bool barrierDismissible = true,
  }) async {
    return showDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (dialogContext) => SimpleDialog(
        title: Text(title),
        children: options.map((option) {
          final bool isSelected = option == selected;
          return SimpleDialogOption(
            onPressed: () => Navigator.of(dialogContext).pop(option),
            child: Row(
              children: [
                if (getIcon != null)
                  Icon(
                    getIcon(option),
                    size: 20,
                    color: isSelected
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).hintColor,
                  ),
                if (getIcon != null) const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    getLabel(option),
                    style: TextStyle(
                      fontWeight: isSelected ? FontWeight.bold : null,
                      color: isSelected
                          ? Theme.of(context).colorScheme.primary
                          : null,
                    ),
                  ),
                ),
                if (isSelected)
                  Icon(
                    Icons.check,
                    color: Theme.of(context).colorScheme.primary,
                    size: 18,
                  ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}
