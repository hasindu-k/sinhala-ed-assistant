import 'package:flutter/material.dart';
import '../../data/models/user.dart'; // adjust if you move UserRole

class RoleDropdown extends StatelessWidget {
  final UserRole? value;
  final ValueChanged<UserRole?> onChanged;
  final List<UserRole> allowed;

  const RoleDropdown({
    super.key,
    required this.value,
    required this.onChanged,
    this.allowed = const [UserRole.student, UserRole.teacher],
  });

  String _label(UserRole r) =>
      r.name[0].toUpperCase() + r.name.substring(1).toLowerCase();

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<UserRole>(
      value: value,
      decoration: const InputDecoration(labelText: 'Select Role'),
      items: allowed
          .map((r) => DropdownMenuItem(value: r, child: Text(_label(r))))
          .toList(),
      onChanged: onChanged,
    );
  }
}
