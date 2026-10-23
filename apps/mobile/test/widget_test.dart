import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:personal_swing_intelligence/main.dart';

void main() {
  test('application root is SwingApp, not a generated MyApp placeholder', () {
    const widget = SwingApp();
    expect(widget, isA<StatelessWidget>());
  });
}
