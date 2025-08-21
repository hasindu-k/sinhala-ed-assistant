// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_db.dart';

// ignore_for_file: type=lint
class $DocumentsTable extends Documents
    with TableInfo<$DocumentsTable, Document> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $DocumentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _contentMeta = const VerificationMeta(
    'content',
  );
  @override
  late final GeneratedColumn<String> content = GeneratedColumn<String>(
    'content',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [id, title, content, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'documents';
  @override
  VerificationContext validateIntegrity(
    Insertable<Document> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    }
    if (data.containsKey('content')) {
      context.handle(
        _contentMeta,
        content.isAcceptableOrUnknown(data['content']!, _contentMeta),
      );
    } else if (isInserting) {
      context.missing(_contentMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Document map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Document(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      ),
      content: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}content'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $DocumentsTable createAlias(String alias) {
    return $DocumentsTable(attachedDatabase, alias);
  }
}

class Document extends DataClass implements Insertable<Document> {
  final String id;
  final String? title;
  final String content;
  final DateTime createdAt;
  const Document({
    required this.id,
    this.title,
    required this.content,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    if (!nullToAbsent || title != null) {
      map['title'] = Variable<String>(title);
    }
    map['content'] = Variable<String>(content);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  DocumentsCompanion toCompanion(bool nullToAbsent) {
    return DocumentsCompanion(
      id: Value(id),
      title: title == null && nullToAbsent
          ? const Value.absent()
          : Value(title),
      content: Value(content),
      createdAt: Value(createdAt),
    );
  }

  factory Document.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Document(
      id: serializer.fromJson<String>(json['id']),
      title: serializer.fromJson<String?>(json['title']),
      content: serializer.fromJson<String>(json['content']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'title': serializer.toJson<String?>(title),
      'content': serializer.toJson<String>(content),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  Document copyWith({
    String? id,
    Value<String?> title = const Value.absent(),
    String? content,
    DateTime? createdAt,
  }) => Document(
    id: id ?? this.id,
    title: title.present ? title.value : this.title,
    content: content ?? this.content,
    createdAt: createdAt ?? this.createdAt,
  );
  Document copyWithCompanion(DocumentsCompanion data) {
    return Document(
      id: data.id.present ? data.id.value : this.id,
      title: data.title.present ? data.title.value : this.title,
      content: data.content.present ? data.content.value : this.content,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Document(')
          ..write('id: $id, ')
          ..write('title: $title, ')
          ..write('content: $content, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, title, content, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Document &&
          other.id == this.id &&
          other.title == this.title &&
          other.content == this.content &&
          other.createdAt == this.createdAt);
}

class DocumentsCompanion extends UpdateCompanion<Document> {
  final Value<String> id;
  final Value<String?> title;
  final Value<String> content;
  final Value<DateTime> createdAt;
  final Value<int> rowid;
  const DocumentsCompanion({
    this.id = const Value.absent(),
    this.title = const Value.absent(),
    this.content = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  DocumentsCompanion.insert({
    required String id,
    this.title = const Value.absent(),
    required String content,
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       content = Value(content);
  static Insertable<Document> custom({
    Expression<String>? id,
    Expression<String>? title,
    Expression<String>? content,
    Expression<DateTime>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (title != null) 'title': title,
      if (content != null) 'content': content,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  DocumentsCompanion copyWith({
    Value<String>? id,
    Value<String?>? title,
    Value<String>? content,
    Value<DateTime>? createdAt,
    Value<int>? rowid,
  }) {
    return DocumentsCompanion(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (content.present) {
      map['content'] = Variable<String>(content.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('DocumentsCompanion(')
          ..write('id: $id, ')
          ..write('title: $title, ')
          ..write('content: $content, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $EmbeddingsTable extends Embeddings
    with TableInfo<$EmbeddingsTable, Embedding> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EmbeddingsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _docIdMeta = const VerificationMeta('docId');
  @override
  late final GeneratedColumn<String> docId = GeneratedColumn<String>(
    'doc_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _chunkIndexMeta = const VerificationMeta(
    'chunkIndex',
  );
  @override
  late final GeneratedColumn<int> chunkIndex = GeneratedColumn<int>(
    'chunk_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _vectorMeta = const VerificationMeta('vector');
  @override
  late final GeneratedColumn<Uint8List> vector = GeneratedColumn<Uint8List>(
    'vector',
    aliasedName,
    false,
    type: DriftSqlType.blob,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [docId, chunkIndex, vector];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'embeddings';
  @override
  VerificationContext validateIntegrity(
    Insertable<Embedding> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('doc_id')) {
      context.handle(
        _docIdMeta,
        docId.isAcceptableOrUnknown(data['doc_id']!, _docIdMeta),
      );
    } else if (isInserting) {
      context.missing(_docIdMeta);
    }
    if (data.containsKey('chunk_index')) {
      context.handle(
        _chunkIndexMeta,
        chunkIndex.isAcceptableOrUnknown(data['chunk_index']!, _chunkIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_chunkIndexMeta);
    }
    if (data.containsKey('vector')) {
      context.handle(
        _vectorMeta,
        vector.isAcceptableOrUnknown(data['vector']!, _vectorMeta),
      );
    } else if (isInserting) {
      context.missing(_vectorMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {docId, chunkIndex};
  @override
  Embedding map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Embedding(
      docId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}doc_id'],
      )!,
      chunkIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}chunk_index'],
      )!,
      vector: attachedDatabase.typeMapping.read(
        DriftSqlType.blob,
        data['${effectivePrefix}vector'],
      )!,
    );
  }

  @override
  $EmbeddingsTable createAlias(String alias) {
    return $EmbeddingsTable(attachedDatabase, alias);
  }
}

class Embedding extends DataClass implements Insertable<Embedding> {
  final String docId;
  final int chunkIndex;
  final Uint8List vector;
  const Embedding({
    required this.docId,
    required this.chunkIndex,
    required this.vector,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['doc_id'] = Variable<String>(docId);
    map['chunk_index'] = Variable<int>(chunkIndex);
    map['vector'] = Variable<Uint8List>(vector);
    return map;
  }

  EmbeddingsCompanion toCompanion(bool nullToAbsent) {
    return EmbeddingsCompanion(
      docId: Value(docId),
      chunkIndex: Value(chunkIndex),
      vector: Value(vector),
    );
  }

  factory Embedding.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Embedding(
      docId: serializer.fromJson<String>(json['docId']),
      chunkIndex: serializer.fromJson<int>(json['chunkIndex']),
      vector: serializer.fromJson<Uint8List>(json['vector']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'docId': serializer.toJson<String>(docId),
      'chunkIndex': serializer.toJson<int>(chunkIndex),
      'vector': serializer.toJson<Uint8List>(vector),
    };
  }

  Embedding copyWith({String? docId, int? chunkIndex, Uint8List? vector}) =>
      Embedding(
        docId: docId ?? this.docId,
        chunkIndex: chunkIndex ?? this.chunkIndex,
        vector: vector ?? this.vector,
      );
  Embedding copyWithCompanion(EmbeddingsCompanion data) {
    return Embedding(
      docId: data.docId.present ? data.docId.value : this.docId,
      chunkIndex: data.chunkIndex.present
          ? data.chunkIndex.value
          : this.chunkIndex,
      vector: data.vector.present ? data.vector.value : this.vector,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Embedding(')
          ..write('docId: $docId, ')
          ..write('chunkIndex: $chunkIndex, ')
          ..write('vector: $vector')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(docId, chunkIndex, $driftBlobEquality.hash(vector));
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Embedding &&
          other.docId == this.docId &&
          other.chunkIndex == this.chunkIndex &&
          $driftBlobEquality.equals(other.vector, this.vector));
}

class EmbeddingsCompanion extends UpdateCompanion<Embedding> {
  final Value<String> docId;
  final Value<int> chunkIndex;
  final Value<Uint8List> vector;
  final Value<int> rowid;
  const EmbeddingsCompanion({
    this.docId = const Value.absent(),
    this.chunkIndex = const Value.absent(),
    this.vector = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  EmbeddingsCompanion.insert({
    required String docId,
    required int chunkIndex,
    required Uint8List vector,
    this.rowid = const Value.absent(),
  }) : docId = Value(docId),
       chunkIndex = Value(chunkIndex),
       vector = Value(vector);
  static Insertable<Embedding> custom({
    Expression<String>? docId,
    Expression<int>? chunkIndex,
    Expression<Uint8List>? vector,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (docId != null) 'doc_id': docId,
      if (chunkIndex != null) 'chunk_index': chunkIndex,
      if (vector != null) 'vector': vector,
      if (rowid != null) 'rowid': rowid,
    });
  }

  EmbeddingsCompanion copyWith({
    Value<String>? docId,
    Value<int>? chunkIndex,
    Value<Uint8List>? vector,
    Value<int>? rowid,
  }) {
    return EmbeddingsCompanion(
      docId: docId ?? this.docId,
      chunkIndex: chunkIndex ?? this.chunkIndex,
      vector: vector ?? this.vector,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (docId.present) {
      map['doc_id'] = Variable<String>(docId.value);
    }
    if (chunkIndex.present) {
      map['chunk_index'] = Variable<int>(chunkIndex.value);
    }
    if (vector.present) {
      map['vector'] = Variable<Uint8List>(vector.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EmbeddingsCompanion(')
          ..write('docId: $docId, ')
          ..write('chunkIndex: $chunkIndex, ')
          ..write('vector: $vector, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDb extends GeneratedDatabase {
  _$AppDb(QueryExecutor e) : super(e);
  $AppDbManager get managers => $AppDbManager(this);
  late final $DocumentsTable documents = $DocumentsTable(this);
  late final $EmbeddingsTable embeddings = $EmbeddingsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [documents, embeddings];
}

typedef $$DocumentsTableCreateCompanionBuilder =
    DocumentsCompanion Function({
      required String id,
      Value<String?> title,
      required String content,
      Value<DateTime> createdAt,
      Value<int> rowid,
    });
typedef $$DocumentsTableUpdateCompanionBuilder =
    DocumentsCompanion Function({
      Value<String> id,
      Value<String?> title,
      Value<String> content,
      Value<DateTime> createdAt,
      Value<int> rowid,
    });

class $$DocumentsTableFilterComposer
    extends Composer<_$AppDb, $DocumentsTable> {
  $$DocumentsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get content => $composableBuilder(
    column: $table.content,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$DocumentsTableOrderingComposer
    extends Composer<_$AppDb, $DocumentsTable> {
  $$DocumentsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get content => $composableBuilder(
    column: $table.content,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$DocumentsTableAnnotationComposer
    extends Composer<_$AppDb, $DocumentsTable> {
  $$DocumentsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get content =>
      $composableBuilder(column: $table.content, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$DocumentsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $DocumentsTable,
          Document,
          $$DocumentsTableFilterComposer,
          $$DocumentsTableOrderingComposer,
          $$DocumentsTableAnnotationComposer,
          $$DocumentsTableCreateCompanionBuilder,
          $$DocumentsTableUpdateCompanionBuilder,
          (Document, BaseReferences<_$AppDb, $DocumentsTable, Document>),
          Document,
          PrefetchHooks Function()
        > {
  $$DocumentsTableTableManager(_$AppDb db, $DocumentsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$DocumentsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$DocumentsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$DocumentsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String?> title = const Value.absent(),
                Value<String> content = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => DocumentsCompanion(
                id: id,
                title: title,
                content: content,
                createdAt: createdAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                Value<String?> title = const Value.absent(),
                required String content,
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => DocumentsCompanion.insert(
                id: id,
                title: title,
                content: content,
                createdAt: createdAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$DocumentsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $DocumentsTable,
      Document,
      $$DocumentsTableFilterComposer,
      $$DocumentsTableOrderingComposer,
      $$DocumentsTableAnnotationComposer,
      $$DocumentsTableCreateCompanionBuilder,
      $$DocumentsTableUpdateCompanionBuilder,
      (Document, BaseReferences<_$AppDb, $DocumentsTable, Document>),
      Document,
      PrefetchHooks Function()
    >;
typedef $$EmbeddingsTableCreateCompanionBuilder =
    EmbeddingsCompanion Function({
      required String docId,
      required int chunkIndex,
      required Uint8List vector,
      Value<int> rowid,
    });
typedef $$EmbeddingsTableUpdateCompanionBuilder =
    EmbeddingsCompanion Function({
      Value<String> docId,
      Value<int> chunkIndex,
      Value<Uint8List> vector,
      Value<int> rowid,
    });

class $$EmbeddingsTableFilterComposer
    extends Composer<_$AppDb, $EmbeddingsTable> {
  $$EmbeddingsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get docId => $composableBuilder(
    column: $table.docId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get chunkIndex => $composableBuilder(
    column: $table.chunkIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<Uint8List> get vector => $composableBuilder(
    column: $table.vector,
    builder: (column) => ColumnFilters(column),
  );
}

class $$EmbeddingsTableOrderingComposer
    extends Composer<_$AppDb, $EmbeddingsTable> {
  $$EmbeddingsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get docId => $composableBuilder(
    column: $table.docId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get chunkIndex => $composableBuilder(
    column: $table.chunkIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<Uint8List> get vector => $composableBuilder(
    column: $table.vector,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$EmbeddingsTableAnnotationComposer
    extends Composer<_$AppDb, $EmbeddingsTable> {
  $$EmbeddingsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get docId =>
      $composableBuilder(column: $table.docId, builder: (column) => column);

  GeneratedColumn<int> get chunkIndex => $composableBuilder(
    column: $table.chunkIndex,
    builder: (column) => column,
  );

  GeneratedColumn<Uint8List> get vector =>
      $composableBuilder(column: $table.vector, builder: (column) => column);
}

class $$EmbeddingsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $EmbeddingsTable,
          Embedding,
          $$EmbeddingsTableFilterComposer,
          $$EmbeddingsTableOrderingComposer,
          $$EmbeddingsTableAnnotationComposer,
          $$EmbeddingsTableCreateCompanionBuilder,
          $$EmbeddingsTableUpdateCompanionBuilder,
          (Embedding, BaseReferences<_$AppDb, $EmbeddingsTable, Embedding>),
          Embedding,
          PrefetchHooks Function()
        > {
  $$EmbeddingsTableTableManager(_$AppDb db, $EmbeddingsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EmbeddingsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EmbeddingsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EmbeddingsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> docId = const Value.absent(),
                Value<int> chunkIndex = const Value.absent(),
                Value<Uint8List> vector = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => EmbeddingsCompanion(
                docId: docId,
                chunkIndex: chunkIndex,
                vector: vector,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String docId,
                required int chunkIndex,
                required Uint8List vector,
                Value<int> rowid = const Value.absent(),
              }) => EmbeddingsCompanion.insert(
                docId: docId,
                chunkIndex: chunkIndex,
                vector: vector,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$EmbeddingsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $EmbeddingsTable,
      Embedding,
      $$EmbeddingsTableFilterComposer,
      $$EmbeddingsTableOrderingComposer,
      $$EmbeddingsTableAnnotationComposer,
      $$EmbeddingsTableCreateCompanionBuilder,
      $$EmbeddingsTableUpdateCompanionBuilder,
      (Embedding, BaseReferences<_$AppDb, $EmbeddingsTable, Embedding>),
      Embedding,
      PrefetchHooks Function()
    >;

class $AppDbManager {
  final _$AppDb _db;
  $AppDbManager(this._db);
  $$DocumentsTableTableManager get documents =>
      $$DocumentsTableTableManager(_db, _db.documents);
  $$EmbeddingsTableTableManager get embeddings =>
      $$EmbeddingsTableTableManager(_db, _db.embeddings);
}
