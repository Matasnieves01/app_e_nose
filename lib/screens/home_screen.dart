import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/tcp_service.dart';
import '../state/app_state.dart';
import '../widgets/glucose_chart.dart';
import '../widgets/result_card.dart';
import '../widgets/sensor_card.dart';
import '../widgets/status_chip.dart';
import 'settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('E-Nose · Glucosa'),
        actions: [
          Consumer<AppState>(
            builder: (_, state, _) => Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(child: StatusChip(status: state.status)),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
      ),
      body: Consumer<AppState>(
        builder: (context, state, _) {
          final r = state.lastReading;
          return RefreshIndicator(
            onRefresh: () => state.connect(),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (state.lastError != null) ...[
                  _errorBanner(state),
                  const SizedBox(height: 12),
                ],
                _infoBanner(),
                const SizedBox(height: 12),
                _measureCard(context, state),
                const SizedBox(height: 12),
                ResultCard(
                  result: state.lastPrediction,
                  hasPrediction: state.hasPrediction,
                ),
                const SizedBox(height: 16),
                GlucoseChart(history: state.glucoseHistory),
                const SizedBox(height: 16),
                const Text(
                  'Arreglo de sensores',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 10),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.15,
                  children: [
                    SensorCard(
                      name: 'MQ-7',
                      detected: 'Monoxido de carbono (CO)',
                      value: r.co,
                      unit: 'ppm',
                      icon: Icons.cloud,
                      color: Colors.blueGrey,
                    ),
                    SensorCard(
                      name: 'MQ-3',
                      detected: 'Alcohol',
                      value: r.alcohol,
                      unit: 'ppm',
                      icon: Icons.local_bar,
                      color: Colors.deepPurple,
                    ),
                    SensorCard(
                      name: 'TGS1820',
                      detected: 'Acetona',
                      value: r.acetone,
                      unit: 'ppm',
                      icon: Icons.science,
                      color: Colors.teal,
                    ),
                  ],
                ),
                const SizedBox(height: 80),
              ],
            ),
          );
        },
      ),
      floatingActionButton: Consumer<AppState>(
        builder: (context, state, _) {
          final connected = state.status == ConnStatus.connected;
          final connecting = state.status == ConnStatus.connecting;

          void onPressed() {
            if (connected) {
              state.disconnect();
            } else if (state.settings.hasHost) {
              state.connect();
            } else {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
            }
          }

          return FloatingActionButton.extended(
            onPressed: connecting ? null : onPressed,
            backgroundColor: connected ? Colors.red.shade600 : null,
            icon: Icon(connected ? Icons.wifi_off : Icons.wifi),
            label: Text(
              connected
                  ? 'Desconectar'
                  : state.settings.hasHost
                      ? 'Conectar'
                      : 'Configurar IP',
            ),
          );
        },
      ),
    );
  }

  Widget _measureCard(BuildContext context, AppState state) {
    final connected = state.status == ConnStatus.connected;

    switch (state.measureState) {
      case MeasureState.preparing:
        return _measureBusy(
          color: Colors.orange,
          icon: Icons.hourglass_top,
          title: 'Preparando sensores...',
          subtitle: 'Listo para detectar en',
          seconds: state.countdown,
          total: AppState.prepSeconds,
          onStop: state.stopMeasurement,
        );
      case MeasureState.measuring:
        return _measureBusy(
          color: Colors.green,
          icon: Icons.sensors,
          title: 'Detectando aliento...',
          subtitle: 'Termina en',
          seconds: state.countdown,
          total: AppState.measureSeconds,
          onStop: state.stopMeasurement,
        );
      case MeasureState.idle:
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: connected ? state.startMeasurement : null,
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    icon: const Icon(Icons.play_circle_fill),
                    label: const Text(
                      'Iniciar medicion',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
                if (!connected)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      'Conecta el Arduino para poder medir',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                    ),
                  ),
              ],
            ),
          ),
        );
    }
  }

  Widget _measureBusy({
    required Color color,
    required IconData icon,
    required String title,
    required String subtitle,
    required int seconds,
    required int total,
    required VoidCallback onStop,
  }) {
    return Card(
      color: color.withValues(alpha: 0.06),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: color.withValues(alpha: 0.4)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            SizedBox(
              width: 56,
              height: 56,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: total == 0 ? null : seconds / total,
                    color: color,
                    backgroundColor: color.withValues(alpha: 0.15),
                  ),
                  Text(
                    '$seconds',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: color,
                      fontSize: 18,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: color, size: 18),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '$subtitle ${seconds}s',
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 12.5),
                  ),
                ],
              ),
            ),
            TextButton(
              onPressed: onStop,
              child: const Text('Detener'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _errorBanner(AppState state) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.red, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              state.lastError ?? '',
              style: const TextStyle(color: Colors.red, fontSize: 12.5),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 18, color: Colors.red),
            onPressed: state.clearError,
          ),
        ],
      ),
    );
  }

  Widget _infoBanner() {
    const color = Color(0xFF1565C0);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: const Row(
        children: [
          Icon(Icons.memory, color: color, size: 20),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'La inferencia se ejecuta en el Arduino UNO Q. La app recibe y '
              'muestra los resultados por Bluetooth.',
              style: TextStyle(color: color, fontSize: 12.5),
            ),
          ),
        ],
      ),
    );
  }
}
