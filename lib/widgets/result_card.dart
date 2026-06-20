import 'package:flutter/material.dart';

import '../models/prediction_result.dart';

/// Tarjeta principal con el resultado de los modelos: clasificacion
/// (sano/diabetico) y estimacion de glucosa en mg/dL.
class ResultCard extends StatelessWidget {
  final PredictionResult result;

  /// `true` cuando el UNO Q ya envio un resultado de prediccion.
  final bool hasPrediction;

  const ResultCard({
    super.key,
    required this.result,
    required this.hasPrediction,
  });

  @override
  Widget build(BuildContext context) {
    final glucoseColor = switch (result.glucoseLevel) {
      GlucoseLevel.hypo => Colors.indigo,
      GlucoseLevel.normal => Colors.green,
      GlucoseLevel.elevated => Colors.orange,
      GlucoseLevel.high => Colors.red,
    };

    return Card(
      color: glucoseColor.withValues(alpha: 0.06),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: glucoseColor.withValues(alpha: 0.4)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.bloodtype, color: glucoseColor),
                const SizedBox(width: 8),
                const Text(
                  'Estimacion de glucosa',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                ),
                const Spacer(),
              ],
            ),
            const SizedBox(height: 16),
            if (!hasPrediction)
              Text(
                'Esperando resultado del Arduino UNO Q...',
                style: TextStyle(color: Colors.grey.shade600),
              )
            else ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    result.glucoseMgDl.toStringAsFixed(0),
                    style: TextStyle(
                      fontSize: 52,
                      fontWeight: FontWeight.bold,
                      color: glucoseColor,
                      height: 1,
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Padding(
                    padding: EdgeInsets.only(bottom: 8),
                    child: Text('mg/dL', style: TextStyle(fontSize: 16)),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              _pill(result.glucoseLevel.label, glucoseColor),
              const Divider(height: 28),
              Row(
                children: [
                  Icon(
                    result.isDiabetic
                        ? Icons.warning_amber_rounded
                        : Icons.check_circle_outline,
                    color: result.isDiabetic ? Colors.red : Colors.green,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Clasificacion: ${result.classificationLabel}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: result.diabetesProbability,
                  minHeight: 8,
                  backgroundColor: Colors.grey.shade300,
                  color: result.isDiabetic ? Colors.red : Colors.green,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Probabilidad de diabetes: '
                '${(result.diabetesProbability * 100).toStringAsFixed(0)}%',
                style: TextStyle(color: Colors.grey.shade700, fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _pill(String text, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          text,
          style: TextStyle(color: color, fontWeight: FontWeight.w700),
        ),
      );
}
