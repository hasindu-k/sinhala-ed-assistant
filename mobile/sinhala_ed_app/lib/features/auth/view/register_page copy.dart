import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../data/models/teacher.dart';
import '../../../data/models/user.dart';
import '../../../data/models/student.dart';
import '../../../data/services/firestore_service.dart';
import '../controller/auth_controller.dart';
import '../../../presentation/routes/app_routes.dart';
import '../../../presentation/routes/navigation_service.dart';
import 'package:sinhala_ed_app/core/widgets/app_widgets.dart';

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
              const VSpace(24),
              const AppLogo(height: 100),
              const VSpace(32),
              AppTextField(controller: _nameController, label: 'Full Name'),
              const VSpace(12),
              AppTextField(
                  controller: _emailController,
                  label: 'Email',
                  keyboardType: TextInputType.emailAddress),
              const VSpace(12),
              AppTextField(
                  controller: _phoneController,
                  label: 'Phone Number',
                  keyboardType: TextInputType.phone),
              const VSpace(12),
              RoleDropdown(
                value: _selectedRole,
                onChanged: (r) => setState(() => _selectedRole = r),
              ),
              const VSpace(12),
              if (_selectedRole == UserRole.student) ...[
                AppTextField(controller: _gradeController, label: 'Grade'),
                const VSpace(12),
              ] else if (_selectedRole == UserRole.teacher) ...[
                AppTextField(
                    controller: _subjectsController,
                    label: 'Subjects (comma separated)'),
                const VSpace(12),
              ],
              PasswordField(controller: _passwordController),
              const VSpace(24),
              LoadingButton(
                isLoading: _isLoading,
                onPressed: _register,
                label: 'Register',
              ),
              const VSpace(16),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text('Already have an account? '),
                  LinkText(
                    text: 'Login',
                    onTap: () => NavigationService.navigateToReplacement(
                        AppRoutes.login),
                  ),
                ],
              ),
            ],
          )),
    );
  }
}
