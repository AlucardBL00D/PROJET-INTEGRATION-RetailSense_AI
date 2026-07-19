import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class ForecastScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ForecastScreen({super.key, required this.apiClient});

  @override
  State<ForecastScreen> createState() => _ForecastScreenState();
}

class _ForecastScreenState extends State<ForecastScreen> {
  final _ordersController = TextEditingController(
    text: '18,20,17,23,22,26,29,24',
  );
  final _horizonController = TextEditingController(text: '7');

  bool _loading = false;
  String? _error;
  List<double> _forecast = const [];

  @override
  void dispose() {
    _ordersController.dispose();
    _horizonController.dispose();
    super.dispose();
  }

  Future<void> _runForecast() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final values = _ordersController.text
          .split(',')
          .map((entry) => double.parse(entry.trim()))
          .toList();
      final horizon = int.parse(_horizonController.text.trim());
      final response = await widget.apiClient.predictDemand(
        recentDailyOrders: values,
        horizonDays: horizon,
      );
      final forecast = (response['forecast'] as List<dynamic>)
          .map((item) => (item as num).toDouble())
          .toList();
      setState(() {
        _forecast = forecast;
        _loading = false;
      });
    } catch (exc) {
      setState(() {
        _error = exc.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          'Prevision de demande',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        const Text('Entrez une serie historique de commandes journalieres.'),
        const SizedBox(height: 14),
        const ScreenIntroCard(
          title: 'A quoi sert la Prevision ventes',
          description:
              'Cette section anticipe les volumes a venir pour aider la planification operationnelle et commerciale.',
          bullets: [
            'Ajuster le stock selon la demande attendue.',
            'Planifier les promotions et les ressources equipe.',
            'Reduire les ruptures et les surstocks.',
          ],
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _ordersController,
          decoration: const InputDecoration(
            labelText: 'Historique (comma separated)',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: 240,
          child: TextField(
            controller: _horizonController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Horizon (jours)',
              border: OutlineInputBorder(),
            ),
          ),
        ),
        const SizedBox(height: 14),
        FilledButton.icon(
          onPressed: _loading ? null : _runForecast,
          icon: const Icon(Icons.timeline),
          label: Text(_loading ? 'Calcul...' : 'Lancer la prevision'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (_forecast.isNotEmpty) ...[
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(height: 240, child: _buildChart(_forecast)),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Forecast: ${_forecast.map((e) => e.toStringAsFixed(1)).join(', ')}',
          ),
          const SizedBox(height: 6),
          Text(_businessSummary(_forecast)),
        ],
      ],
    );
  }

  String _businessSummary(List<double> values) {
    if (values.length < 2) {
      return 'Demande prevue stable sur la periode selectionnee.';
    }
    final start = values.first;
    final end = values.last;
    if (start <= 0) {
      return 'Demande prevue pour ${values.length} jours a venir.';
    }
    final deltaPct = ((end - start) / start) * 100;
    if (deltaPct >= 5) {
      return 'Demande prevue en hausse de ${deltaPct.toStringAsFixed(1)}% sur ${values.length} jours.';
    }
    if (deltaPct <= -5) {
      return 'Demande prevue en baisse de ${deltaPct.abs().toStringAsFixed(1)}% sur ${values.length} jours.';
    }
    return 'Demande prevue globalement stable sur ${values.length} jours.';
  }

  Widget _buildChart(List<double> forecast) {
    final spots = <FlSpot>[];
    for (var i = 0; i < forecast.length; i++) {
      spots.add(FlSpot(i.toDouble(), forecast[i]));
    }
    return LineChart(
      LineChartData(
        borderData: FlBorderData(show: false),
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: const Color(0xFFDB6E2D),
            barWidth: 3,
            dotData: const FlDotData(show: true),
          ),
        ],
      ),
    );
  }
}
