import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class ClientScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ClientScreen({super.key, required this.apiClient});

  @override
  State<ClientScreen> createState() => _ClientScreenState();
}

class _ClientScreenState extends State<ClientScreen> {
  final _formKey = GlobalKey<FormState>();
  final _recencyController = TextEditingController(text: '250');
  final _frequencyController = TextEditingController(text: '2');
  final _monetaryController = TextEditingController(text: '450');
  final _priceController = TextEditingController(text: '150');
  final _reviewController = TextEditingController(
    text: 'Excellent service and fast delivery',
  );

  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _segmentation;
  Map<String, dynamic>? _churn;
  Map<String, dynamic>? _sentiment;

  @override
  void dispose() {
    _recencyController.dispose();
    _frequencyController.dispose();
    _monetaryController.dispose();
    _priceController.dispose();
    _reviewController.dispose();
    super.dispose();
  }

  Future<void> _analyzeClient() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final segmentation = await widget.apiClient.predictSegmentation(
        recency: double.parse(_recencyController.text),
        frequency: double.parse(_frequencyController.text),
        monetary: double.parse(_monetaryController.text),
      );
      final churn = await widget.apiClient.predictChurn(
        totalPrice: double.parse(_priceController.text),
        category: 'electronics',
        paymentType: 'credit_card',
        customerState: 'SP',
      );
      final sentiment = await widget.apiClient.predictSentiment(
        _reviewController.text,
      );

      setState(() {
        _segmentation = segmentation;
        _churn = churn;
        _sentiment = sentiment;
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
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Fiche client',
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Segment + risque de churn + sentiment client en un clic.',
            ),
            const SizedBox(height: 14),
            const ScreenIntroCard(
              title: 'A quoi sert la Fiche client IA',
              description:
                  'Cet ecran transforme quelques indicateurs client en decisions actionnables pour la retention et la relation client.',
              bullets: [
                'Identifier le segment client automatiquement.',
                'Estimer la probabilite de churn pour prioriser les actions.',
                'Analyser le ton des avis clients pour mesurer la satisfaction.',
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 14,
              runSpacing: 14,
              children: [
                _numberField(_recencyController, 'Recency (jours, >=0)'),
                _numberField(_frequencyController, 'Frequency (>=1)'),
                _numberField(_monetaryController, 'Monetary (>=0)'),
                _numberField(_priceController, 'Panier total'),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _reviewController,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Avis client',
                border: OutlineInputBorder(),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Entrez un avis';
                }
                return null;
              },
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: _loading ? null : _analyzeClient,
              icon: const Icon(Icons.analytics),
              label: Text(_loading ? 'Analyse...' : 'Analyser'),
            ),
            const SizedBox(height: 12),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: Colors.red)),
            if (_segmentation != null)
              _ResultTile(
                title: 'Segmentation',
                value: 'Cluster ${_segmentation!['cluster']}',
                model: _segmentation!['model']?.toString(),
              ),
            if (_churn != null)
              _ResultTile(
                title: 'Risque churn',
                value:
                    '${(((_churn!['risk_probability'] as num?) ?? 0) * 100).toStringAsFixed(1)}% (classe ${_churn!['prediction']})',
                model: _churn!['model']?.toString(),
              ),
            if (_sentiment != null)
              _ResultTile(
                title: 'Sentiment',
                value:
                    '${_sentiment!['label']} (conf ${_sentiment!['confidence']})',
                model: _sentiment!['model']?.toString(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _numberField(TextEditingController controller, String label) {
    return SizedBox(
      width: 240,
      child: TextFormField(
        controller: controller,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        validator: (value) {
          if (value == null || value.trim().isEmpty) {
            return 'Obligatoire';
          }
          if (double.tryParse(value) == null) {
            return 'Nombre invalide';
          }
          return null;
        },
      ),
    );
  }
}

class _ResultTile extends StatelessWidget {
  final String title;
  final String value;
  final String? model;

  const _ResultTile({required this.title, required this.value, this.model});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(title),
        subtitle: Text('$value\nModele: ${model ?? 'non disponible'}'),
      ),
    );
  }
}
