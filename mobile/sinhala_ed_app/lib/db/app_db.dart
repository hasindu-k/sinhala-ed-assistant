import 'dart:typed_data';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

part 'app_db.g.dart';

class Documents extends Table {
  TextColumn get id => text()(); // uuid
  TextColumn get title => text().nullable()();
  TextColumn get content => text()(); // raw text
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {id};
}

// Optional: store embeddings later (as BLOB)
class Embeddings extends Table {
  TextColumn get docId => text()();
  IntColumn get chunkIndex => integer()(); // which chunk this vector belongs to
  BlobColumn get vector => blob()(); // Uint8List bytes

  @override
  Set<Column> get primaryKey => {docId, chunkIndex};
}

@DriftDatabase(tables: [Documents, Embeddings])
class AppDb extends _$AppDb {
  AppDb() : super(_open());

  @override
  int get schemaVersion => 1;

  // Upsert a document
  Future<void> upsertDocument(String id, String? title, String content) async {
    await into(documents).insertOnConflictUpdate(
      DocumentsCompanion(
        id: Value(id),
        title: Value(title),
        content: Value(content),
        // createdAt will use default if omitted
      ),
    );
  }

  Future<List<Document>> allDocs() => select(documents).get();

  // Save a Float64List embedding as bytes
  Future<void> saveEmbedding(String docId, int chunk, Float64List vec) async {
    final Uint8List bytes = vec.buffer.asUint8List();
    await into(embeddings).insertOnConflictUpdate(
      EmbeddingsCompanion(
        docId: Value(docId),
        chunkIndex: Value(chunk),
        vector: Value(bytes),
      ),
    );
  }
}

LazyDatabase _open() {
  return LazyDatabase(() async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File(p.join(dir.path, 'app.db'));
    // Background open avoids main-thread I/O jank
    return NativeDatabase.createInBackground(file);
  });
}
