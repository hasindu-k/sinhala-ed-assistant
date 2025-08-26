import 'package:flutter/material.dart';
import 'sinhala_ed_app.dart';
import 'package:firebase_core/firebase_core.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const SinhalaEdApp());
}
