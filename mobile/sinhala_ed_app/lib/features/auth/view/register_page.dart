import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../data/models/teacher.dart';
import '../../../data/models/user.dart';
import '../../../data/models/student.dart';
import '../../../data/services/firestore_service.dart';
import '../controller/auth_controller.dart';
import '../../../presentation/routes/app_routes.dart';
import '../../../presentation/routes/navigation_service.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  final _gradeController = TextEditingController();
  final _phoneController = TextEditingController();
  UserRole? _selectedRole;
  final _subjectsController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _gradeController.dispose();
    _phoneController.dispose();
    _subjectsController.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    final auth = context.read<AuthController>();
    final firestore = FirestoreService();

    setState(() => _isLoading = true);

    try {
      final user = await auth.signUp(
        _emailController.text.trim(),
        _passwordController.text,
      );

      // Update displayName if needed
      if (auth.currentUser != null && _nameController.text.isNotEmpty) {
        await auth.currentUser!.updateDisplayName(_nameController.text);
        await auth.currentUser!.reload();
      }

      if (user != null) {
        // Update displayName
        if (_nameController.text.isNotEmpty) {
          await user.updateDisplayName(_nameController.text);
          await user.reload();
        }

        if (_selectedRole == UserRole.student) {
          // Create Student object
          final student = Student(
            id: user.uid,
            name: _nameController.text,
            email: _emailController.text.trim(),
            phoneNumber: _phoneController.text,
            grade: _gradeController.text,
          );

          // Save to Firestore
          await firestore.createStudent(student);
        } else if (_selectedRole == UserRole.teacher) {
          // Create Teacher object
          final teacher = Teacher(
            id: user.uid,
            name: _nameController.text,
            email: _emailController.text.trim(),
            phoneNumber: _phoneController.text,
            subjects: _subjectsController.text
                .split(',')
                .map((s) => s.trim())
                .where((s) => s.isNotEmpty)
                .toList(),
          );

          // Save to Firestore
          await firestore.createTeacher(teacher);
        }

        // Navigate to home
        NavigationService.navigateToReplacement(AppRoutes.home);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Registration failed: ${e.toString()}')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Register"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            const SizedBox(height: 24),
            Image.asset(
              'assets/images/logo.png',
              height: 100,
            ),
            const SizedBox(height: 64),
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: "Full Name"),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: "Email"),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phoneController,
              decoration: const InputDecoration(labelText: "Phone Number"),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<UserRole>(
              value: _selectedRole,
              decoration: const InputDecoration(labelText: "Select Role"),
              //only Student role and teacher role for display
              items: UserRole.values
                  .where((role) =>
                      role == UserRole.student || role == UserRole.teacher)
                  .map((role) {
                return DropdownMenuItem(
                  value: role,
                  child: Text(
                    role.name[0].toUpperCase() +
                        role.name.substring(1).toLowerCase(),
                  ), // shows enum name
                );
              }).toList(),
              onChanged: (role) {
                setState(() {
                  _selectedRole = role;
                });
              },
            ),
            const SizedBox(height: 12),
            if (_selectedRole == UserRole.student) ...[
              TextField(
                controller: _gradeController,
                decoration: const InputDecoration(labelText: "Grade"),
              ),
              const SizedBox(height: 12),
            ] else if (_selectedRole == UserRole.teacher) ...[
              TextField(
                controller: _subjectsController,
                decoration: const InputDecoration(
                  labelText: "Subjects (comma separated)",
                ),
              ),
              const SizedBox(height: 12),
            ],
            TextField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                labelText: "Password",
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscurePassword ? Icons.visibility : Icons.visibility_off,
                  ),
                  onPressed: () {
                    setState(() {
                      _obscurePassword = !_obscurePassword;
                    });
                  },
                ),
              ),
            ),
            const SizedBox(height: 24),
            _isLoading
                ? const CircularProgressIndicator()
                : SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _register,
                      child: const Text("Register"),
                    ),
                  ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Text("Already have an account? "),
                GestureDetector(
                  onTap: () {
                    NavigationService.navigateToReplacement(AppRoutes.login);
                  },
                  child: const Text(
                    "Login",
                    style: TextStyle(
                      color: Colors.blue,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
