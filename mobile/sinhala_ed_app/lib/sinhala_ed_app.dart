import 'package:flutter/material.dart';
import 'presentation/pages/home_page.dart';

class SinhalaEdApp extends StatelessWidget {
  const SinhalaEdApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sinhala Ed Assistant',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}
