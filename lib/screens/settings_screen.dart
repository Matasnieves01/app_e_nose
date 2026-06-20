import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';

/// Configuracion de la conexion WiFi al UNO Q (IP + puerto).
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _host;
  late TextEditingController _port;

  @override
  void initState() {
    super.initState();
    final s = context.read<AppState>().settings;
    _host = TextEditingController(text: s.host);
    _port = TextEditingController(text: s.port.toString());
  }

  @override
  void dispose() {
    _host.dispose();
    _port.dispose();
    super.dispose();
  }

  Future<void> _saveAndConnect() async {
    if (!_formKey.currentState!.validate()) return;
    final host = _host.text.trim();
    final port = int.tryParse(_port.text.trim()) ?? 8765;
    await context.read<AppState>().connect(host: host, port: port);
    if (!mounted) return;
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Conexion WiFi')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _field(
              _host,
              'IP del UNO Q',
              hint: 'Ej. 192.168.1.100',
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            _field(
              _port,
              'Puerto',
              hint: '8765',
              keyboard: TextInputType.number,
              validator: (v) =>
                  int.tryParse(v ?? '') == null ? 'Numero invalido' : null,
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: _saveAndConnect,
              icon: const Icon(Icons.wifi),
              label: const Text('Guardar y conectar'),
            ),
            const SizedBox(height: 16),
            Card(
              color: Colors.blue.shade50,
              child: const Padding(
                padding: EdgeInsets.all(14),
                child: Text(
                  'El teléfono y el UNO Q deben estar en la misma red Wi-Fi.\n\n'
                  'En el UNO Q corre el puente:\n'
                  '  python3 wifi_host.py\n\n'
                  'Para ver la IP del UNO Q:  hostname -I\n'
                  'Puerto por defecto: 8765.',
                  style: TextStyle(fontSize: 12.5),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(
    TextEditingController c,
    String label, {
    String? hint,
    TextInputType? keyboard,
    String? Function(String?)? validator,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: c,
        keyboardType: keyboard,
        validator: validator,
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }
}
