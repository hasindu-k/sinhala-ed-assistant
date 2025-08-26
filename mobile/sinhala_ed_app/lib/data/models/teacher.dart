import './user.dart';

class Teacher extends User {
  final List<String>? subjects;

  Teacher({
    required super.id,
    required super.name,
    required super.email,
    required super.phoneNumber,
    super.profilePictureUrl,
    this.subjects,
  }) : super(role: UserRole.teacher);
}
