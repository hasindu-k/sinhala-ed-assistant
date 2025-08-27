import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
// import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import 'package:sinhala_ed_app/core/widgets/app_widgets.dart';
import 'package:sinhala_ed_app/data/models/user.dart';
import 'package:sinhala_ed_app/data/services/firestore_service.dart';
import 'package:sinhala_ed_app/features/auth/controller/auth_controller.dart';
import 'package:sinhala_ed_app/features/auth/view/register_page.dart';
import 'mocks.mocks.dart';

void main() {
  late MockAuthController mockAuthController;
  late MockFirestoreService mockFirestoreService;

  setUp(() {
    mockAuthController = MockAuthController();
    mockFirestoreService = MockFirestoreService();
  });

  Future<void> _buildRegisterPage(WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<AuthController>.value(
            value: mockAuthController,
          ),
          Provider<FirestoreService>.value(
            value: mockFirestoreService,
          ),
        ],
        child: const MaterialApp(
          home: RegisterPage(),
        ),
      ),
    );
  }

  testWidgets('renders register form fields', (tester) async {
    await _buildRegisterPage(tester);

    expect(find.byType(TextField), findsNWidgets(4));
    expect(find.byType(DropdownButtonFormField<UserRole>), findsOneWidget);
    expect(find.byType(LoadingButton), findsOneWidget);
  });
}
