import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class AnomalyScreen extends StatefulWidget {
  final ApiClient apiClient;

  const AnomalyScreen({super.key, required this.apiClient});

  @override
  State<AnomalyScreen> createState() => _AnomalyScreenState();
}

class _AnomalyScreenState extends State<AnomalyScreen> {
  final _totalPriceController = TextEditingController(text: '150.0');
  final _totalFreightController = TextEditingController(text: '12.5');
  final _totalWeightController = TextEditingController(text: '2.1');
  final _nItemsController = TextEditingController(text: '3');
  final _maxInstallmentsController = TextEditingController(text: '3');
  final _paymentValueController = TextEditingController(text: '162.5');
  final _deliveryDaysController = TextEditingController(text: '4');
  final _delayDaysController = TextEditingController(text: '0');

  bool _loading = false;
  String? _error;
  double? _score;
  bool? _isAnomaly;
  String? _riskLevel;
  String? _message;

  @override
  void dispose() {
    _totalPriceController.dispose();
    _totalFreightController.dispose();
    _totalWeightController.dispose();
    _nItemsController.dispose();
    _maxInstallmentsController.dispose();
    _paymentValueController.dispose();
    _deliveryDaysController.dispose();
    _delayDaysController.dispose();
    super.dispose();
  }

  Future<void> _runAnomaly() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final totalPrice = double.parse(_totalPriceController.text.trim());
      final totalFreight = double.parse(_totalFreightController.text.trim());
      final totalWeight = double.parse(_totalWeightController.text.trim());
      final nItems = double.parse(_nItemsController.text.trim());
      final maxInstallments = double.parse(
        _maxInstallmentsController.text.trim(),
      );
      final paymentValue = double.parse(_paymentValueController.text.trim());
      final deliveryDays = double.parse(_deliveryDaysController.text.trim());
      final delayDays = double.parse(_delayDaysController.text.trim());

      final response = await widget.apiClient.predictAnomaly(
        totalPrice: totalPrice,
        totalFreight: totalFreight,
        totalWeight: totalWeight,
        nItems: nItems,
        maxInstallments: maxInstallments,
        paymentValue: paymentValue,
        deliveryDays: deliveryDays,
        delayDays: delayDays,
      );
      setState(() {
        _score = (response['anomaly_score'] as num?)?.toDouble();
        _isAnomaly = response['is_anomaly'] as bool?;
        _riskLevel = response['risk_level']?.toString();
        _message = response['message']?.toString();
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
    final hasResult = _score != null && _isAnomaly != null;

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          'Score d\'anomalie',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        const ScreenIntroCard(
          title: 'Objectif',
          description:
              'Detecter des comportements atypiques dans les donnees transactionnelles.',
          bullets: [
            'Signaler des cas potentiellement frauduleux ou inhabituels.',
            'Declencher une verification humaine pour les cas suspects.',
          ],
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            _numberField(_totalPriceController, 'total_price'),
            _numberField(_totalFreightController, 'total_freight'),
            _numberField(_totalWeightController, 'total_weight'),
            _numberField(_nItemsController, 'n_items'),
            _numberField(_maxInstallmentsController, 'max_installments'),
            _numberField(_paymentValueController, 'payment_value'),
            _numberField(_deliveryDaysController, 'delivery_days'),
            _numberField(_delayDaysController, 'delay_days'),
          ],
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _loading ? null : _runAnomaly,
          icon: const Icon(Icons.warning_amber),
          label: Text(_loading ? 'Analyse...' : 'Calculer score'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (hasResult) ...[
          const SizedBox(height: 10),
          Card(
            color: _isAnomaly!
                ? const Color(0xFFFFF1F1)
                : const Color(0xFFEFFAF3),
            child: ListTile(
              leading: Icon(_isAnomaly! ? Icons.warning : Icons.check_circle),
              title: Text(
                'Score d anomalie: ${(_score! * 100).toStringAsFixed(1)}%',
              ),
              subtitle: Text(
                '${_isAnomaly! ? 'Commande inhabituelle detectee' : 'Comportement normal'}\nNiveau de risque: ${_riskLevel ?? 'Faible'}\n${_message ?? ''}',
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _numberField(TextEditingController controller, String label) {
    return SizedBox(
      width: 220,
      child: TextField(
        controller: controller,
        keyboardType: TextInputType.number,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }
}
