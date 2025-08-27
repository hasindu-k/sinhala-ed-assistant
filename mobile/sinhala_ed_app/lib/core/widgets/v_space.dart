import 'package:flutter/widgets.dart';

class VSpace extends StatelessWidget {
  final double h;
  const VSpace(this.h, {super.key});

  @override
  Widget build(BuildContext context) => SizedBox(height: h);
}
