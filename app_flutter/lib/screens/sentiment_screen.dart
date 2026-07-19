import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class SentimentScreen extends StatefulWidget {
  final ApiClient apiClient;

  const SentimentScreen({super.key, required this.apiClient});

  @override
  State<SentimentScreen> createState() => _SentimentScreenState();
}

class _SentimentScreenState extends State<SentimentScreen> {
  final _reviewController = TextEditingController(
    text: 'Excellent service and fast delivery',
  );

  bool _loading = false;
  String? _error;
  String? _label;
  double? _confidence;

  String _labelToFrench(String label) {
    switch (label.toLowerCase()) {
      case 'positive':
        return 'Positif';
      case 'negative':
        return 'Negatif';
      default:
        return label;
    }
  }

  @override
  void dispose() {
    _reviewController.dispose();
    super.dispose();
  }

  Future<void> _runSentiment() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final response = await widget.apiClient.predictSentiment(
        _reviewController.text,
      );

      setState(() {
        _label = response['label']?.toString();
        _confidence = (response['confidence'] as num?)?.toDouble();
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
    final confidencePercent = _confidence == null
        ? null
        : (_confidence!.clamp(0.0, 1.0) * 100);
    final confidenceText = confidencePercent?.toStringAsFixed(1);

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          'Sentiment d\'un avis',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        const ScreenIntroCard(
          title: 'Objectif',
          description:
              'Analyser automatiquement le ton des avis pour mesurer la satisfaction client.',
          bullets: [
            'Identifier avis positifs et negatifs.',
            'Suivre la perception client apres achat.',
          ],
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _reviewController,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Texte de l\'avis',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _loading ? null : _runSentiment,
          icon: const Icon(Icons.reviews),
          label: Text(_loading ? 'Analyse...' : 'Analyser sentiment'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 10),
          Text(_error!, style: const TextStyle(color: Colors.red)),
        ],
        if (_label != null) ...[
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.emoji_emotions_outlined),
                      const SizedBox(width: 8),
                      Text(
                        'Sentiment: ${_labelToFrench(_label!)}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    confidenceText == null
                        ? 'Certitude du modele: non disponible'
                        : 'Certitude du modele: $confidenceText%',
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Etats possibles:',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _stateChip('negative', 'Negatif'),
                      _stateChip('positive', 'Positif'),
                    ],
                  ),
                  if (confidencePercent != null) ...[
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: (confidencePercent / 100).clamp(0.0, 1.0),
                      minHeight: 8,
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _stateChip(String key, String label) {
    final selected = _label?.toLowerCase() == key;
    return Chip(
      avatar: Icon(
        selected ? Icons.check_circle : Icons.circle_outlined,
        size: 18,
      ),
      label: Text(label),
      backgroundColor: selected ? const Color(0xFFFFE5D6) : null,
    );
  }
}
