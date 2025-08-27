import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:sinhala_ed_app/data/models/teacher.dart';
import '../models/student.dart';

class FirestoreService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  Future<void> createStudent(Student student) async {
    await _firestore
        .collection('students')
        .doc(student.id)
        .set(student.toMap());
  }

  Future<void> updateStudent(Student student) async {
    await _firestore
        .collection('students')
        .doc(student.id)
        .update(student.toMap());
  }

  Future<void> createTeacher(Teacher teacher) async {
    await _firestore
        .collection('teachers')
        .doc(teacher.id)
        .set(teacher.toMap());
  }

  Future<void> updateTeacher(Teacher teacher) async {
    await _firestore
        .collection('teachers')
        .doc(teacher.id)
        .update(teacher.toMap());
  }
}
