import 'package:shared_preferences/shared_preferences.dart';

/// Configuracion de conexion WiFi al puente del UNO Q (`wifi_host.py`).
class ConnSettings {
  /// IP del UNO Q en la red local (ver `hostname -I` en el UNO Q).
  final String host;
  final int port;

  const ConnSettings({required this.host, required this.port});

  static const ConnSettings defaults = ConnSettings(
    host: '192.168.1.100',
    port: 8765,
  );

  bool get hasHost => host.trim().isNotEmpty;

  ConnSettings copyWith({String? host, int? port}) =>
      ConnSettings(host: host ?? this.host, port: port ?? this.port);
}

class SettingsService {
  static const _kHost = 'unoq_host';
  static const _kPort = 'unoq_port';

  Future<ConnSettings> load() async {
    final p = await SharedPreferences.getInstance();
    return ConnSettings(
      host: p.getString(_kHost) ?? ConnSettings.defaults.host,
      port: p.getInt(_kPort) ?? ConnSettings.defaults.port,
    );
  }

  Future<void> save(ConnSettings s) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kHost, s.host);
    await p.setInt(_kPort, s.port);
  }
}
