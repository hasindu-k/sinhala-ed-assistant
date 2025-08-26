import 'package:cloud_firestore/cloud_firestore.dart';
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
}
