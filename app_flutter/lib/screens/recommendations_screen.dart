import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

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

  bool _loading = false;
  String? _error;
  List<String> _items = const [];
  String? _model;

  @override
  void dispose() {
    _segmentController.dispose();
    _riskController.dispose();
    _categoriesController.dispose();
    _topKController.dispose();
    super.dispose();
  }

  Future<void> _runRecommendations() async {
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

      setState(() {
        _items = (recommendations['recommendations'] as List<dynamic>)
            .map((item) => item.toString())
            .toList();
        _model = recommendations['model']?.toString();
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
          'Recommandations produits',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        const ScreenIntroCard(
          title: 'A quoi sert Recommandations',
          description:
              'Cet ecran genere des recommandations personnalisees selon le segment et le risque churn du client.',
          bullets: [
            'Proposer des produits pertinents selon le profil client.',
            'Prioriser des offres retention si risque churn eleve.',
            'Ameliorer le panier moyen avec des produits complementaires.',
          ],
        ),
        const SizedBox(height: 12),
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
        FilledButton.icon(
          onPressed: _loading ? null : _runRecommendations,
          icon: const Icon(Icons.recommend),
          label: Text(_loading ? 'Chargement...' : 'Generer recommandations'),
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
          const SizedBox(height: 6),
          Text('Modele: ${_model ?? 'non disponible'}'),
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
