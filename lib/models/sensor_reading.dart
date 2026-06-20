import 'dart:convert';

/// Una lectura del arreglo de sensores de la nariz electronica (E-Nose).
///
/// Estos son los 3 sensores que alimentan los modelos (ver notebooks
/// nb1/nb2). El cuarto feature del modelo, `CO_7`, es la misma lectura del
/// MQ-7 duplicada, por lo que no es un sensor fisico aparte.
///
/// El Arduino UNO Q envia por BLE un JSON con estas lecturas. Las claves son
/// flexibles para tolerar pequenas diferencias en el firmware.
class SensorReading {
  /// MQ-7 -> Monoxido de carbono (CO). Alimenta los features CO y CO_7.
  final double co;

  /// MQ-3 -> Alcohol.
  final double alcohol;

  /// TGS1820 -> Acetona.
  final double acetone;

  /// Momento en el que la app recibio la lectura.
  final DateTime timestamp;

  const SensorReading({
    required this.co,
    required this.alcohol,
    required this.acetone,
    required this.timestamp,
  });

  /// Construye una lectura a partir del payload JSON recibido del dispositivo
  /// (por BLE, una linea de texto JSON).
  factory SensorReading.fromJson(String payload) {
    final dynamic decoded = jsonDecode(payload);
    if (decoded is! Map) {
      throw const FormatException('El payload no es un objeto JSON');
    }
    return SensorReading.fromMap(decoded.cast<String, dynamic>());
  }

  /// Construye una lectura a partir de un mapa ya decodificado.
  ///
  /// Tolera distintas claves (`co`, `mq7`, etc.) para facilitar la integracion
  /// con el firmware del Arduino.
  factory SensorReading.fromMap(Map<String, dynamic> map) {
    double pick(List<String> keys, {double fallback = 0}) {
      for (final k in keys) {
        if (map.containsKey(k) && map[k] != null) {
          final v = map[k];
          if (v is num) return v.toDouble();
          final parsed = double.tryParse(v.toString());
          if (parsed != null) return parsed;
        }
      }
      return fallback;
    }

    return SensorReading(
      co: pick(['co', 'CO', 'mq7', 'mq_7', 'MQ7']),
      alcohol: pick(['alcohol', 'Alcohol', 'mq3', 'mq_3', 'MQ3']),
      acetone: pick(['acetone', 'Acetone', 'acetona', 'mq135', 'tgs', 'tgs1820']),
      timestamp: DateTime.now(),
    );
  }

  /// Lectura en cero, util como estado inicial antes de recibir datos.
  factory SensorReading.empty() => SensorReading(
        co: 0,
        alcohol: 0,
        acetone: 0,
        timestamp: DateTime.now(),
      );

  Map<String, dynamic> toJson() => {
        'co': co,
        'alcohol': alcohol,
        'acetone': acetone,
        'timestamp': timestamp.toIso8601String(),
      };
}
