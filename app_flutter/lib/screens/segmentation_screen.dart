import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class SegmentationScreen extends StatefulWidget {
  final ApiClient apiClient;

  const SegmentationScreen({super.key, required this.apiClient});

  @override
  State<SegmentationScreen> createState() => _SegmentationScreenState();
}

class _SegmentationScreenState extends State<SegmentationScreen> {
  final _recencyController = TextEditingController(text: '0.2');
  final _frequencyController = TextEditingController(text: '0.8');
  final _monetaryController = TextEditingController(text: '0.6');

  bool _loading = false;
  String? _error;
  int? _cluster;

  @override
  void dispose() {
    _recencyController.dispose();
    _frequencyController.dispose();
    _monetaryController.dispose();
    super.dispose();
  }

  Future<void> _runSegmentation() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await widget.apiClient.predictSegmentation(
        recency: double.parse(_recencyController.text),
        frequency: double.parse(_frequencyController.text),
        monetary: double.parse(_monetaryController.text),
      );

      setState(() {
        _cluster = response['cluster'] as int?;
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
          'Segmentation d\'un client',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        const ScreenIntroCard(
          title: 'Objectif',
          description:
              'Attribuer automatiquement un segment client pour personnaliser offres et priorites commerciales.',
          bullets: [
            'Classer les clients selon recence, frequence et valeur.',
            'Identifier rapidement les profils premium ou a reactiver.',
          ],
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _field(_recencyController, 'Recency (0-1)'),
            _field(_frequencyController, 'Frequency (0-1)'),
            _field(_monetaryController, 'Monetary (0-1)'),
          ],
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _loading ? null : _runSegmentation,
          icon: const Icon(Icons.bubble_chart),
          label: Text(_loading ? 'Calcul...' : 'Predire segment'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (_cluster != null) ...[
          const SizedBox(height: 10),
          Card(
            child: ListTile(
              leading: const Icon(Icons.check_circle_outline),
              title: const Text('Segment detecte'),
              subtitle: Text('Cluster $_cluster'),
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
        keyboardType: TextInputType.number,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }
}
