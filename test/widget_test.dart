// Prueba de humo basica de la app E-Nose.

import 'package:flutter_test/flutter_test.dart';

import 'package:e_nose_app/main.dart';

void main() {
  testWidgets('La app arranca y muestra el titulo', (tester) async {
    await tester.pumpWidget(const ENoseApp());
    await tester.pump();

    expect(find.text('E-Nose · Glucosa'), findsOneWidget);
    expect(find.text('Iniciar medicion'), findsOneWidget);
  });
}
