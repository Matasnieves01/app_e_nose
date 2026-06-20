import 'package:flutter/material.dart';

import '../services/tcp_service.dart';

/// Indicador compacto del estado de la conexion WiFi con el UNO Q.
class StatusChip extends StatelessWidget {
  final ConnStatus status;
  const StatusChip({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label, icon) = switch (status) {
      ConnStatus.connected => (Colors.green, 'Conectado', Icons.wifi),
      ConnStatus.connecting => (Colors.orange, 'Conectando...', Icons.wifi_find),
      ConnStatus.error => (Colors.red, 'Error', Icons.wifi_off),
      ConnStatus.disconnected => (Colors.grey, 'Desconectado', Icons.wifi_off),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w600,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
