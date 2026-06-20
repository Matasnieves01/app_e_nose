import 'dart:async';
import 'dart:collection';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../models/prediction_result.dart';
import '../models/sensor_reading.dart';
import '../services/tcp_service.dart';
import '../services/settings_service.dart';

/// Orquesta el flujo: WiFi (TCP) -> recibe sensores + resultados (calculados en
/// el UNO Q) -> UI. Es el unico `ChangeNotifier` que consume la interfaz.
class AppState extends ChangeNotifier {
  final TcpService _net;
  final SettingsService _settingsService;

  AppState({
    TcpService? net,
    SettingsService? settingsService,
  })  : _net = net ?? TcpService(),
        _settingsService = settingsService ?? SettingsService();

  // ---- Estado expuesto a la UI ----
  ConnSettings _settings = ConnSettings.defaults;
  ConnSettings get settings => _settings;

  ConnStatus _status = ConnStatus.disconnected;
  ConnStatus get status => _status;

  SensorReading _lastReading = SensorReading.empty();
  SensorReading get lastReading => _lastReading;
  bool _hasData = false;
  bool get hasData => _hasData;

  PredictionResult _lastPrediction = PredictionResult.empty();
  PredictionResult get lastPrediction => _lastPrediction;

  /// `true` cuando el UNO Q ya envio al menos un resultado de prediccion.
  bool _hasPrediction = false;
  bool get hasPrediction => _hasPrediction;

  String? _lastError;
  String? get lastError => _lastError;

  /// Historial reciente de glucosa estimada para graficar (max 60 puntos).
  static const int _maxHistory = 60;
  final ListQueue<double> _glucoseHistory = ListQueue<double>();
  List<double> get glucoseHistory => _glucoseHistory.toList(growable: false);

  // ---- Sesion de medicion ----
  /// Segundos de preparacion (calentamiento) antes de empezar a detectar.
  static const int prepSeconds = 10;

  /// Duracion de la deteccion antes de parar automaticamente.
  static const int measureSeconds = 20;

  MeasureState _measureState = MeasureState.idle;
  MeasureState get measureState => _measureState;

  int _countdown = 0;
  int get countdown => _countdown;

  Timer? _tick;

  StreamSubscription? _statusSub;
  StreamSubscription? _readingSub;
  StreamSubscription? _errorSub;

  Future<void> init() async {
    _settings = await _settingsService.load();

    _statusSub = _net.statusStream.listen((s) {
      _status = s;
      if (s == ConnStatus.disconnected || s == ConnStatus.error) {
        cancelMeasurement();
      }
      notifyListeners();
    });
    _readingSub = _net.lineStream.listen(_onLine);
    _errorSub = _net.errorStream.listen((e) {
      _lastError = e;
      notifyListeners();
    });

    notifyListeners();
  }

  /// Procesa una linea JSON del UNO Q: contiene las lecturas de sensores y,
  /// opcionalmente, el resultado de los modelos (glucosa + clasificacion).
  void _onLine(String line) {
    final Map<String, dynamic> map;
    try {
      final decoded = jsonDecode(line);
      if (decoded is! Map) throw const FormatException('no es objeto');
      map = decoded.cast<String, dynamic>();
    } catch (_) {
      _lastError = 'Mensaje invalido: $line';
      notifyListeners();
      return;
    }

    _lastReading = SensorReading.fromMap(map);
    _hasData = true;

    final prediction = PredictionResult.fromMap(map);
    if (prediction != null) {
      _lastPrediction = prediction;
      _hasPrediction = true;
      _glucoseHistory.addLast(prediction.glucoseMgDl);
      while (_glucoseHistory.length > _maxHistory) {
        _glucoseHistory.removeFirst();
      }
    }
    notifyListeners();
  }

  // ---- Acciones de conexion ----
  /// Guarda host/puerto y se conecta al UNO Q por WiFi.
  Future<void> connect({String? host, int? port}) async {
    _lastError = null;
    if (host != null || port != null) {
      _settings = _settings.copyWith(host: host, port: port);
      await _settingsService.save(_settings);
      notifyListeners();
    }
    await _net.connect(_settings.host, _settings.port);
  }

  Future<void> disconnect() async {
    cancelMeasurement();
    await _net.disconnect();
  }

  // ---- Sesion de medicion ----
  /// Inicia una medicion: avisa al Arduino (START), cuenta la preparacion y
  /// luego detecta por [measureSeconds] antes de parar solo.
  Future<void> startMeasurement() async {
    if (_status != ConnStatus.connected) {
      _lastError = 'Conecta el UNO Q antes de medir.';
      notifyListeners();
      return;
    }
    _hasPrediction = false;
    await _net.sendCommand('START');

    _measureState = MeasureState.preparing;
    _countdown = prepSeconds;
    notifyListeners();

    _tick?.cancel();
    _tick = Timer.periodic(const Duration(seconds: 1), (_) {
      _countdown--;
      if (_countdown <= 0) {
        if (_measureState == MeasureState.preparing) {
          // Termino la preparacion -> empieza a detectar.
          _measureState = MeasureState.measuring;
          _countdown = measureSeconds;
        } else {
          // Termino la deteccion -> para sola.
          stopMeasurement();
          return;
        }
      }
      notifyListeners();
    });
  }

  /// Detiene la medicion y avisa al Arduino (STOP).
  Future<void> stopMeasurement() async {
    _tick?.cancel();
    _tick = null;
    _measureState = MeasureState.idle;
    _countdown = 0;
    notifyListeners();
    await _net.sendCommand('STOP');
  }

  /// Cancela sin enviar STOP (p. ej. al desconectar).
  void cancelMeasurement() {
    _tick?.cancel();
    _tick = null;
    _measureState = MeasureState.idle;
    _countdown = 0;
  }

  Future<void> updateSettings(ConnSettings newSettings) async {
    _settings = newSettings;
    await _settingsService.save(newSettings);
    notifyListeners();
  }

  void clearError() {
    _lastError = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _tick?.cancel();
    _statusSub?.cancel();
    _readingSub?.cancel();
    _errorSub?.cancel();
    _net.dispose();
    super.dispose();
  }
}

/// Estado de la sesion de medicion controlada desde la app.
enum MeasureState {
  /// Sin medir (en espera).
  idle,

  /// Preparando: el Arduino calienta/estabiliza (cuenta regresiva).
  preparing,

  /// Detectando: recibiendo lecturas.
  measuring,
}
