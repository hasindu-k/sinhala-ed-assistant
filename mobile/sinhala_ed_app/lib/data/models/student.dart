import './user.dart';

class Student extends User {
  final String grade;

  Student({
    required super.id,
    required super.name,
    required super.email,
    required super.phoneNumber,
    super.profilePictureUrl,
    required this.grade,
  }) : super(role: UserRole.student);
}
