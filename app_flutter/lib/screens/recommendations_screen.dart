import 'package:flutter/material.dart';

import '../services/api_client.dart';

class RecommendationsScreen extends StatefulWidget {
  final ApiClient apiClient;

  const RecommendationsScreen({super.key, required this.apiClient});

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  final _segmentController = TextEditingController(text: '2');
  final _riskController = TextEditingController(text: '0.74');
  final _categoriesController = TextEditingController(
    text: 'electronics,accessories',
  );
  final _topKController = TextEditingController(text: '5');
  final _anomalyFeaturesController = TextEditingController(
    text: '0.1,0.2,0.3,0.1,0.0,0.5,0.2,0.1',
  );

  bool _loading = false;
  String? _error;
  List<String> _items = const [];
  Map<String, dynamic>? _anomaly;

  @override
  void dispose() {
    _segmentController.dispose();
    _riskController.dispose();
    _categoriesController.dispose();
    _topKController.dispose();
    _anomalyFeaturesController.dispose();
    super.dispose();
  }

  Future<void> _runInference() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final categories = _categoriesController.text
          .split(',')
          .map((value) => value.trim())
          .where((value) => value.isNotEmpty)
          .toList();

      final recommendations = await widget.apiClient.predictRecommendations(
        segment: int.parse(_segmentController.text),
        churnRisk: double.parse(_riskController.text),
        recentCategories: categories,
        topK: int.parse(_topKController.text),
      );

      final features = _anomalyFeaturesController.text
          .split(',')
          .map((value) => double.parse(value.trim()))
          .toList();

      final anomaly = await widget.apiClient.predictAnomaly(features);

      setState(() {
        _items = (recommendations['recommendations'] as List<dynamic>)
            .map((item) => item.toString())
            .toList();
        _anomaly = anomaly;
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
          'Recommandations + anomalie',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _smallField(_segmentController, 'Segment'),
            _smallField(_riskController, 'Risque churn'),
            _smallField(_topKController, 'Top K'),
          ],
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _categoriesController,
          decoration: const InputDecoration(
            labelText: 'Categories recentes',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _anomalyFeaturesController,
          decoration: const InputDecoration(
            labelText: 'Features anomalie (comma separated)',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _loading ? null : _runInference,
          icon: const Icon(Icons.recommend),
          label: Text(_loading ? 'Chargement...' : 'Generer les resultats'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (_items.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text(
            'Produits recommandes',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ..._items.map(
            (item) => Card(
              child: ListTile(
                leading: const Icon(Icons.shopping_bag),
                title: Text(item),
              ),
            ),
          ),
        ],
        if (_anomaly != null) ...[
          const SizedBox(height: 12),
          Card(
            color: ((_anomaly!['is_anomaly'] as bool?) ?? false)
                ? const Color(0xFFFFF1F1)
                : const Color(0xFFEFFAF3),
            child: ListTile(
              leading: Icon(
                ((_anomaly!['is_anomaly'] as bool?) ?? false)
                    ? Icons.warning
                    : Icons.check_circle,
              ),
              title: Text('Score anomalie: ${_anomaly!['anomaly_score']}'),
              subtitle: Text('Seuil: ${_anomaly!['threshold']}'),
            ),
          ),
        ],
      ],
    );
  }

  Widget _smallField(TextEditingController controller, String label) {
    return SizedBox(
      width: 180,
      child: TextField(
        controller: controller,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }
}
