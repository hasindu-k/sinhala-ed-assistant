import 'user.dart';

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

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phoneNumber': phoneNumber,
      'role': role.toString().split('.').last,
      'profilePictureUrl': profilePictureUrl,
      'subjects': subjects,
    };
  }

  factory Teacher.fromMap(Map<String, dynamic> map) {
    return Teacher(
      id: map['id'],
      name: map['name'],
      email: map['email'],
      phoneNumber: map['phoneNumber'],
      profilePictureUrl: map['profilePictureUrl'],
      subjects: List<String>.from(map['subjects'] ?? []),
    );
  }
}
