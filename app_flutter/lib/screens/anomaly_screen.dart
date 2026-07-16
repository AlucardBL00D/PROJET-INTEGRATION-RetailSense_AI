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
  static const int _expectedFeatureCount = 7;

  final _featuresController = TextEditingController(
    text: '0.1,0.2,0.3,0.1,0.0,0.5,0.2',
  );

  bool _loading = false;
  String? _error;
  double? _score;
  double? _threshold;
  bool? _isAnomaly;

  @override
  void dispose() {
    _featuresController.dispose();
    super.dispose();
  }

  Future<void> _runAnomaly() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final values = _featuresController.text
          .split(',')
          .map((v) => double.parse(v.trim()))
          .toList();

      if (values.length != _expectedFeatureCount) {
        setState(() {
          _error =
              'Le modele attend $_expectedFeatureCount valeurs, mais ${values.length} ont ete fournies.';
          _loading = false;
        });
        return;
      }

      final response = await widget.apiClient.predictAnomaly(values);
      setState(() {
        _score = (response['anomaly_score'] as num?)?.toDouble();
        _threshold = (response['threshold'] as num?)?.toDouble();
        _isAnomaly = response['is_anomaly'] as bool?;
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
    final hasResult =
        _score != null && _threshold != null && _isAnomaly != null;

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
        TextField(
          controller: _featuresController,
          decoration: const InputDecoration(
            labelText: 'Features (7 valeurs separees par des virgules)',
            border: OutlineInputBorder(),
          ),
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
              title: Text('Score: ${_score!.toStringAsFixed(3)}'),
              subtitle: Text(
                'Seuil: ${_threshold!.toStringAsFixed(3)} - ${_isAnomaly! ? 'Anomalie detectee' : 'Comportement normal'}',
              ),
            ),
          ),
        ],
      ],
    );
  }
}
