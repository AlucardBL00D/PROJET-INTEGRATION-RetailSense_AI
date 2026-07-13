import 'package:flutter/material.dart';

import '../services/api_client.dart';

class ClientScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ClientScreen({super.key, required this.apiClient});

  @override
  State<ClientScreen> createState() => _ClientScreenState();
}

class _ClientScreenState extends State<ClientScreen> {
  final _formKey = GlobalKey<FormState>();
  final _recencyController = TextEditingController(text: '0.2');
  final _frequencyController = TextEditingController(text: '0.8');
  final _monetaryController = TextEditingController(text: '0.6');
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
            const SizedBox(height: 16),
            Wrap(
              spacing: 14,
              runSpacing: 14,
              children: [
                _numberField(_recencyController, 'Recency (0-1)'),
                _numberField(_frequencyController, 'Frequency (0-1)'),
                _numberField(_monetaryController, 'Monetary (0-1)'),
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
              ),
            if (_churn != null)
              _ResultTile(
                title: 'Risque churn',
                value:
                    '${(((_churn!['risk_probability'] as num?) ?? 0) * 100).toStringAsFixed(1)}% (classe ${_churn!['prediction']})',
              ),
            if (_sentiment != null)
              _ResultTile(
                title: 'Sentiment',
                value:
                    '${_sentiment!['label']} (conf ${_sentiment!['confidence']})',
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

  const _ResultTile({required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(title),
        subtitle: Text(value),
      ),
    );
  }
}
