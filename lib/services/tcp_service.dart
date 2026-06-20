import 'dart:async';
import 'dart:convert';
import 'dart:io';

enum ConnStatus { disconnected, connecting, connected, error }

/// Transporte por WiFi: se conecta por TCP al puente que corre en el host del
/// UNO Q (`wifi_host.py`). Recibe lineas JSON (sensores + resultado) y envia
/// comandos (START/STOP de la medicion).
class TcpService {
  Socket? _socket;
  StreamSubscription? _socketSub;

  final _statusController = StreamController<ConnStatus>.broadcast();
  final _lineController = StreamController<String>.broadcast();
  final _errorController = StreamController<String>.broadcast();

  Stream<ConnStatus> get statusStream => _statusController.stream;

  /// Cada linea JSON completa recibida del UNO Q.
  Stream<String> get lineStream => _lineController.stream;
  Stream<String> get errorStream => _errorController.stream;

  ConnStatus _status = ConnStatus.disconnected;
  ConnStatus get status => _status;

  final StringBuffer _rxBuffer = StringBuffer();

  void _setStatus(ConnStatus s) {
    _status = s;
    if (!_statusController.isClosed) _statusController.add(s);
  }

  Future<void> connect(String host, int port) async {
    await disconnect();
    _setStatus(ConnStatus.connecting);
    try {
      _socket = await Socket.connect(
        host,
        port,
        timeout: const Duration(seconds: 8),
      );
    } catch (e) {
      _setStatus(ConnStatus.error);
      _emitError('No se pudo conectar a $host:$port — $e');
      return;
    }

    _setStatus(ConnStatus.connected);
    _socketSub = _socket!.listen(
      _onData,
      onError: (e) {
        _emitError('Error de red: $e');
        _setStatus(ConnStatus.error);
      },
      onDone: () {
        if (_status != ConnStatus.error) _setStatus(ConnStatus.disconnected);
      },
      cancelOnError: true,
    );
  }

  void _onData(List<int> bytes) {
    _rxBuffer.write(utf8.decode(bytes, allowMalformed: true));
    final content = _rxBuffer.toString();
    if (!content.contains('\n')) return;

    final lines = content.split('\n');
    _rxBuffer
      ..clear()
      ..write(lines.removeLast()); // ultima parte (posiblemente incompleta)

    for (final line in lines) {
      final trimmed = line.trim();
      if (trimmed.isNotEmpty) _lineController.add(trimmed);
    }
  }

  /// Envia un comando al UNO Q (p. ej. "START" / "STOP").
  Future<void> sendCommand(String cmd) async {
    final s = _socket;
    if (s == null) {
      _emitError('No hay conexion para enviar el comando.');
      return;
    }
    try {
      s.write('$cmd\n');
      await s.flush();
    } catch (e) {
      _emitError('No se pudo enviar el comando: $e');
    }
  }

  void _emitError(String msg) {
    if (!_errorController.isClosed) _errorController.add(msg);
  }

  Future<void> disconnect() async {
    await _socketSub?.cancel();
    _socketSub = null;
    _rxBuffer.clear();
    try {
      await _socket?.close();
    } catch (_) {}
    _socket?.destroy();
    _socket = null;
    _setStatus(ConnStatus.disconnected);
  }

  void dispose() {
    _socketSub?.cancel();
    _socket?.destroy();
    _statusController.close();
    _lineController.close();
    _errorController.close();
  }
}
