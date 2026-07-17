import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class ChurnScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ChurnScreen({super.key, required this.apiClient});

  @override
  State<ChurnScreen> createState() => _ChurnScreenState();
}

class _ChurnScreenState extends State<ChurnScreen> {
  final _priceController = TextEditingController(text: '150');
  final _categoryController = TextEditingController(text: 'electronics');
  final _paymentTypeController = TextEditingController(text: 'credit_card');
  final _stateController = TextEditingController(text: 'SP');

  bool _loading = false;
  String? _error;
  int? _prediction;
  double? _risk;
  String? _model;

  @override
  void dispose() {
    _priceController.dispose();
    _categoryController.dispose();
    _paymentTypeController.dispose();
    _stateController.dispose();
    super.dispose();
  }

  Future<void> _runChurn() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await widget.apiClient.predictChurn(
        totalPrice: double.parse(_priceController.text),
        category: _categoryController.text.trim(),
        paymentType: _paymentTypeController.text.trim(),
        customerState: _stateController.text.trim(),
      );

      setState(() {
        _prediction = response['prediction'] as int?;
        _risk = (response['risk_probability'] as num?)?.toDouble();
        _model = response['model']?.toString();
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
    final riskPct = _risk == null ? null : (_risk! * 100).toStringAsFixed(1);

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          'Prediction de churn',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        const ScreenIntroCard(
          title: 'Objectif',
          description:
              'Estimer la probabilite de perte client pour declencher des actions de retention au bon moment.',
          bullets: [
            'Prioriser les clients a fort risque.',
            'Lancer des offres retention ciblees.',
          ],
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _field(_priceController, 'Panier total'),
            _field(_categoryController, 'Categorie principale'),
            _field(_paymentTypeController, 'Type de paiement'),
            _field(_stateController, 'Etat client'),
          ],
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _loading ? null : _runChurn,
          icon: const Icon(Icons.person_off),
          label: Text(_loading ? 'Calcul...' : 'Predire churn'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (_prediction != null && riskPct != null) ...[
          const SizedBox(height: 10),
          Card(
            child: ListTile(
              leading: const Icon(Icons.insights),
              title: Text('Risque: $riskPct%'),
              subtitle: Text(
                'Classe predite: $_prediction\nModele: ${_model ?? 'non disponible'}',
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _field(TextEditingController controller, String label) {
    return SizedBox(
      width: 220,
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
