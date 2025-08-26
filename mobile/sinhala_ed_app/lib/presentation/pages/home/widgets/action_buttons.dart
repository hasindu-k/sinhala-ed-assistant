// lib/presentation/pages/home/widgets/action_buttons.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/theme.dart';
import '../../../routes/app_routes.dart';

class ActionButtonsRow extends StatelessWidget {
  const ActionButtonsRow({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        FilledButton.icon(
          onPressed: () {
            // TODO: wire to voice Q&A
            // Navigator.pushNamed(context, AppRoutes.voiceQa);
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Voice Q&A coming soon')),
            );
          },
          icon: const Icon(Icons.mic),
          label: const Text('Ask by Voice'),
        ),
        const SizedBox(width: 12),
        OutlinedButton.icon(
          onPressed: () {
            // TODO: wire to OCR module
            // Navigator.pushNamed(context, AppRoutes.ocr);
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('OCR coming soon')),
            );
          },
          icon: const Icon(Icons.upload_file),
          label: const Text('Scan Document'),
        ),
      ],
    );
  }
}
