class User {
  final String id;
  final String name;
  final String email;
  final String phoneNumber;
  final UserRole role;
  final String? profilePictureUrl;

  User({
    required this.id,
    required this.name,
    required this.email,
    required this.phoneNumber,
    required this.role,
    this.profilePictureUrl,
  });
}

enum UserRole { admin, student, teacher, otherUsers }
