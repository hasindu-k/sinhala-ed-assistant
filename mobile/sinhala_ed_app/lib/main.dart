// lib/main.dart
import 'package:flutter/material.dart';
import 'db/app_db.dart';

late final AppDb db;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  db = AppDb();
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(home: Home());
}

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  final _title = TextEditingController();
  final _content = TextEditingController();
  List<Document> docs = [];

  Future<void> save() async {
    await db.upsertDocument(
      DateTime.now().millisecondsSinceEpoch.toString(),
      _title.text,
      _content.text,
    );
    docs = await db.allDocs();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Docs')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _title,
              decoration: const InputDecoration(labelText: 'Title'),
            ),
            TextField(
              controller: _content,
              decoration: const InputDecoration(labelText: 'Content'),
            ),
            const SizedBox(height: 8),
            FilledButton(onPressed: save, child: const Text('Save')),
            const Divider(),
            Expanded(
              child: ListView.builder(
                itemCount: docs.length,
                itemBuilder: (_, i) => ListTile(
                  title: Text(docs[i].title ?? '(untitled)'),
                  subtitle: Text(
                    docs[i].content,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
