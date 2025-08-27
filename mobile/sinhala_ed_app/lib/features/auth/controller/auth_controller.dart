import 'package:flutter/material.dart';
import '../../../data/services/auth_service.dart';
import 'package:firebase_auth/firebase_auth.dart';

class AuthController extends ChangeNotifier {
  final AuthService _authService = AuthService();

  User? currentUser;

  AuthController() {
    _authService.authStateChanges.listen((user) {
      currentUser = user;
      notifyListeners();
    });
  }

  Future<void> signIn(String email, String password) async {
    await _authService.signIn(email, password);
  }

  Future<User?> signUp(String email, String password) async {
    return await _authService.signUp(email, password);
  }

  Future<void> signOut() async {
    await _authService.signOut();
  }
}
