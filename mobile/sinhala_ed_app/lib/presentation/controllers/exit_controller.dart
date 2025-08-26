import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import '../../core/utils/dialogs.dart';

/// Keeps back-press/exit behavior out of the widget tree
class ExitController {
  void handleSystemBack(BuildContext context, bool didPop, Object? result) {
    if (didPop) return;
    _confirmAndExit(context);
  }

  Future<void> _confirmAndExit(BuildContext context) async {
    final shouldExit = await AppDialogs.confirm(
      context,
      title: 'Exit App',
      message: 'Are you sure you want to exit?',
      okText: 'Exit',
      okIsDestructive: true,
      barrierDismissible: false,
    );

    if (context.mounted && shouldExit) {
      SystemNavigator.pop();
    }
  }
}
