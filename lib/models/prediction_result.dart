/// Resultado de las dos tareas de inferencia descritas en el articulo:
///   1. Clasificacion: sano vs. diabetico.
///   2. Regresion: estimacion del nivel de glucosa en sangre (mg/dL).
///
/// La inferencia se ejecuta **en el Arduino UNO Q** (lado Linux). La app solo
/// recibe estos resultados ya calculados por BLE y los muestra.
class PredictionResult {
  /// Probabilidad [0, 1] de que el patron corresponda a una persona diabetica.
  final double diabetesProbability;

  /// Nivel de glucosa estimado en mg/dL.
  final double glucoseMgDl;

  final DateTime timestamp;

  const PredictionResult({
    required this.diabetesProbability,
    required this.glucoseMgDl,
    required this.timestamp,
  });

  bool get isDiabetic => diabetesProbability >= 0.5;

  String get classificationLabel => isDiabetic ? 'Diabetico' : 'Sano';

  /// Categoria glucemica clinica de referencia.
  /// El dataset del articulo no contempla hipoglucemia (< 70 mg/dL), por lo que
  /// el sistema queda restringido a discriminar normal vs. hiperglucemia.
  GlucoseLevel get glucoseLevel {
    if (glucoseMgDl < 70) return GlucoseLevel.hypo;
    if (glucoseMgDl <= 140) return GlucoseLevel.normal;
    if (glucoseMgDl <= 180) return GlucoseLevel.elevated;
    return GlucoseLevel.high;
  }

  factory PredictionResult.empty() => PredictionResult(
        diabetesProbability: 0,
        glucoseMgDl: 0,
        timestamp: DateTime.now(),
      );

  /// Extrae el resultado del modelo desde el JSON enviado por el UNO Q.
  ///
  /// Devuelve `null` si el mensaje no trae campos de prediccion (p. ej. si solo
  /// llegaron lecturas crudas de sensores). Tolera varias claves para el nivel
  /// de glucosa y la clasificacion.
  static PredictionResult? fromMap(Map<String, dynamic> map) {
    double? pick(List<String> keys) {
      for (final k in keys) {
        if (map.containsKey(k) && map[k] != null) {
          final v = map[k];
          if (v is num) return v.toDouble();
          final parsed = double.tryParse(v.toString());
          if (parsed != null) return parsed;
        }
      }
      return null;
    }

    final glucose = pick(['glucose', 'glucosa', 'bgl', 'glucose_mgdl', 'glucemia']);
    final prob = pick(['prob', 'probability', 'diabetes_prob', 'prob_diabetes']);

    // Clasificacion como flag (0/1) o como texto ("sano"/"diabetico").
    bool? classFlag;
    for (final k in ['diabetes', 'class', 'clase', 'diabetic', 'resultado']) {
      if (map.containsKey(k) && map[k] != null) {
        final v = map[k].toString().toLowerCase().trim();
        if (v == '1' || v == 'true' || v.startsWith('diab')) {
          classFlag = true;
        } else if (v == '0' || v == 'false' || v.startsWith('san') || v == 'normal') {
          classFlag = false;
        }
        break;
      }
    }

    // Sin ningun campo de prediccion -> no hay resultado que mostrar.
    if (glucose == null && prob == null && classFlag == null) return null;

    final double probability = prob != null
        ? prob.clamp(0.0, 1.0)
        : (classFlag == true ? 1.0 : 0.0);

    return PredictionResult(
      diabetesProbability: probability,
      glucoseMgDl: glucose ?? 0,
      timestamp: DateTime.now(),
    );
  }
}

enum GlucoseLevel { hypo, normal, elevated, high }

extension GlucoseLevelInfo on GlucoseLevel {
  String get label => switch (this) {
        GlucoseLevel.hypo => 'Hipoglucemia',
        GlucoseLevel.normal => 'Normal',
        GlucoseLevel.elevated => 'Elevado',
        GlucoseLevel.high => 'Hiperglucemia',
      };
}
