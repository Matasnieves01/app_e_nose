import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

/// Grafico de linea con el historial reciente de glucosa estimada.
class GlucoseChart extends StatelessWidget {
  final List<double> history;
  const GlucoseChart({super.key, required this.history});

  @override
  Widget build(BuildContext context) {
    if (history.length < 2) {
      return Card(
        child: Container(
          height: 180,
          alignment: Alignment.center,
          child: Text(
            'El historial aparecera aqui\ncuando lleguen mas lecturas.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey.shade600),
          ),
        ),
      );
    }

    final spots = <FlSpot>[
      for (var i = 0; i < history.length; i++) FlSpot(i.toDouble(), history[i]),
    ];
    final minY = (history.reduce((a, b) => a < b ? a : b) - 20).clamp(0, 400).toDouble();
    final maxY = (history.reduce((a, b) => a > b ? a : b) + 20).toDouble();

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 18, 18, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(left: 6, bottom: 12),
              child: Text(
                'Tendencia de glucosa (mg/dL)',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
            SizedBox(
              height: 160,
              child: LineChart(
                LineChartData(
                  minY: minY,
                  maxY: maxY,
                  gridData: FlGridData(show: true, drawVerticalLine: false),
                  titlesData: FlTitlesData(
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    bottomTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 38,
                        interval: ((maxY - minY) / 4).clamp(1, 1000),
                        getTitlesWidget: (v, meta) => Text(
                          v.toStringAsFixed(0),
                          style: const TextStyle(fontSize: 10),
                        ),
                      ),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: const Color(0xFF1565C0),
                      barWidth: 3,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: const Color(0xFF1565C0).withValues(alpha: 0.12),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
