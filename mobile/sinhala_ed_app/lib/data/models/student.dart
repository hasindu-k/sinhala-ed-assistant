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

  // Factory to create Student from Firestore
  factory Student.fromMap(Map<String, dynamic> data, String id) {
    return Student(
      id: id,
      name: data['name'] ?? '',
      email: data['email'] ?? '',
      phoneNumber: data['phoneNumber'] ?? '',
      profilePictureUrl: data['profilePictureUrl'],
      grade: data['grade'] ?? '',
    );
  }

  // Convert Student to Map for Firestore
  Map<String, dynamic> toMap() {
    return {
      'name': name,
      'email': email,
      'phoneNumber': phoneNumber,
      'profilePictureUrl': profilePictureUrl,
      'role': role.name,
      'grade': grade,
    };
  }
}
