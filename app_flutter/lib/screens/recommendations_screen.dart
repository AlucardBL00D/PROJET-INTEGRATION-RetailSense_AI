import 'package:flutter/material.dart';

import '../services/api_client.dart';

class RecommendationsScreen extends StatefulWidget {
  final ApiClient apiClient;

  const RecommendationsScreen({super.key, required this.apiClient});

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  final _recencyController = TextEditingController(text: '250');
  final _frequencyController = TextEditingController(text: '2');
  final _monetaryController = TextEditingController(text: '450');
  final _priceController = TextEditingController(text: '150');
  final _categoryController = TextEditingController(text: 'electronics');
  final _paymentTypeController = TextEditingController(text: 'credit_card');
  final _stateController = TextEditingController(text: 'SP');
  final _categoriesController = TextEditingController(
    text: 'electronics,accessories',
  );

  bool _loading = false;
  int _progressStep = 0;
  String? _error;
  List<String> _items = const [];
  int? _clusterId;
  String? _segmentLabel;
  String? _segmentDescription;
  double? _churnRisk;
  String? _riskLevel;
  String? _churnMessage;

  @override
  void dispose() {
    _recencyController.dispose();
    _frequencyController.dispose();
    _monetaryController.dispose();
    _priceController.dispose();
    _categoryController.dispose();
    _paymentTypeController.dispose();
    _stateController.dispose();
    _categoriesController.dispose();
    super.dispose();
  }

  Future<void> _runRecommendations() async {
    final recency = double.tryParse(_recencyController.text);
    final frequency = double.tryParse(_frequencyController.text);
    final monetary = double.tryParse(_monetaryController.text);
    final totalPrice = double.tryParse(_priceController.text);

    if (recency == null ||
        frequency == null ||
        monetary == null ||
        totalPrice == null) {
      setState(() {
        _error = 'Veuillez verifier les valeurs numeriques de la fiche client.';
      });
      return;
    }

    setState(() {
      _loading = true;
      _progressStep = 0;
      _error = null;
    });

    try {
      final rawCategories = _categoriesController.text
          .split(',')
          .map((value) => value.trim())
          .where((value) => value.isNotEmpty)
          .toList();
      final categories = _normalizeCategories(rawCategories);
      final normalizedCategory = _normalizeSingleCategory(
        _categoryController.text.trim(),
      );
      final normalizedPaymentType = _paymentTypeController.text
          .trim()
          .toLowerCase();
      final normalizedState = _stateController.text.trim().toUpperCase();

      debugPrint(
        '[RecommendationsScreen] Input payload recency=$recency frequency=$frequency monetary=$monetary totalPrice=$totalPrice category=$normalizedCategory paymentType=$normalizedPaymentType state=$normalizedState recentCategories=$categories',
      );

      final segmentation = await widget.apiClient.predictSegmentation(
        recency: recency,
        frequency: frequency,
        monetary: monetary,
      );
      debugPrint(
        '[RecommendationsScreen] Segmentation response: $segmentation',
      );

      final clusterId = segmentation['cluster_id'] as int? ?? -1;
      final segmentLabel =
          segmentation['segment']?.toString() ?? 'Profil client';
      final segmentDescription =
          segmentation['description']?.toString() ??
          'Profil detecte sur les indicateurs RFM.';
      setState(() {
        _progressStep = 1;
      });

      final churn = await widget.apiClient.predictChurn(
        totalPrice: totalPrice,
        category: normalizedCategory,
        paymentType: normalizedPaymentType,
        customerState: normalizedState,
        recency: recency,
        frequency: frequency,
        monetary: monetary,
        recentCategories: categories,
      );
      debugPrint('[RecommendationsScreen] Churn response: $churn');

      final churnRisk = (churn['churn_probability'] as num?)?.toDouble() ?? 0.0;
      final riskLevel = churn['risk_level']?.toString() ?? 'Moyen';
      final churnMessage =
          churn['message']?.toString() ??
          'Une baisse d activite est detectee pour ce client.';
      setState(() {
        _progressStep = 2;
      });

      final recommendations = await widget.apiClient.predictRecommendations(
        segment: clusterId,
        churnRisk: churnRisk,
        recentCategories: categories,
      );
      debugPrint(
        '[RecommendationsScreen] Recommendations response: $recommendations',
      );

      setState(() {
        _items = (recommendations['recommendations'] as List<dynamic>)
            .map((item) => item.toString())
            .toList();
        _clusterId = clusterId;
        _segmentLabel = segmentLabel;
        _segmentDescription = segmentDescription;
        _churnRisk = churnRisk;
        _riskLevel = riskLevel;
        _churnMessage = churnMessage;
        _progressStep = 3;
        _loading = false;
      });
    } catch (exc) {
      setState(() {
        _error = 'Impossible de generer les recommandations: $exc';
        _progressStep = 0;
        _loading = false;
      });
    }
  }

  String getRiskLevel(double risk) {
    if (risk < 0.20) {
      return 'Faible';
    }
    if (risk < 0.50) {
      return 'Moyen';
    }
    if (risk < 0.75) {
      return 'Eleve';
    }
    return 'Critique';
  }

  Color _getRiskColor(double risk) {
    if (risk < 0.20) {
      return const Color(0xFF2E7D32);
    }
    if (risk < 0.50) {
      return const Color(0xFFF9A825);
    }
    if (risk < 0.75) {
      return const Color(0xFFEF6C00);
    }
    return const Color(0xFFC62828);
  }

  double _displayChurnRisk(double rawRisk) {
    final risk = rawRisk.clamp(0.0, 1.0);
    if (risk < 0.40) {
      return risk * 0.80;
    }
    if (risk < 0.70) {
      return 0.32 + (risk - 0.40) * 0.90;
    }
    return (0.59 + (risk - 0.70) * 1.35).clamp(0.0, 1.0);
  }

  String generateRecommendationMessage({
    required int segment,
    required double risk,
  }) {
    if (risk >= 0.75) {
      return 'Le client presente un fort risque de depart. Une offre speciale ou un suivi personnalise est conseille.';
    }

    if (segment == 1 && risk < 0.20) {
      return 'Excellent client. Il effectue des achats regulierement. Proposez des produits complementaires ou premium.';
    }

    if (segment == 1 && risk >= 0.50) {
      return 'Ce client etait fidele mais semble moins actif. Une promotion personnalisee est recommandee.';
    }

    if (segment == 0 && risk < 0.20) {
      return 'Client recemment acquis. Favoriser une bonne premiere experience avec des propositions simples et utiles.';
    }

    if (segment == 3 || risk >= 0.50) {
      return 'Le client montre des signes de desengagement. Une action rapide peut limiter le risque de depart.';
    }

    return 'Profil stable. Continuez des recommandations ciblees pour soutenir la frequence d\'achat.';
  }

  List<String> _getSuggestedActions({
    required int segment,
    required double risk,
  }) {
    if (risk >= 0.75 || segment == 3) {
      return const [
        '💸 Envoyer un coupon personnalise.',
        '📧 Relancer par courriel.',
        '🎯 Mettre en avant des promotions ciblees.',
      ];
    }

    if (segment == 1 && risk < 0.20) {
      return const [
        '⭐ Proposer un produit premium.',
        '🎁 Offrir un programme de fidelite.',
        '🛒 Suggerez des produits complementaires.',
      ];
    }

    if (segment == 0) {
      return const [
        '👋 Presenter les meilleures ventes.',
        '🎁 Offrir une reduction de bienvenue.',
        '⭐ Encourager un deuxieme achat.',
      ];
    }

    return const [
      '🛒 Mettre en avant des produits complementaires.',
      '🎯 Personnaliser les suggestions selon les achats recents.',
      '📈 Suivre la frequence d\'achat sur les prochaines semaines.',
    ];
  }

  String _formatProductName(String rawName) {
    final normalized = rawName.toLowerCase();
    if (normalized.contains('mouse')) {
      return 'Souris sans fil';
    }
    if (normalized.contains('keyboard')) {
      return 'Clavier ergonomique';
    }
    if (normalized.contains('headphone')) {
      return 'Casque audio';
    }

    final tokens = rawName
        .split(RegExp(r'[._\-\s]+'))
        .where((part) => part.trim().isNotEmpty)
        .map(
          (part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .toList();

    if (tokens.isEmpty) {
      return 'Produit recommande';
    }

    return tokens.join(' ');
  }

  List<String> _buildReasonsForProduct() {
    final reasons = <String>[
      'Correspond au profil du client.',
      'Souvent achete avec les produits recents.',
      'Adapte au segment du client.',
    ];

    if ((_churnRisk ?? 0) >= 0.50) {
      reasons.add('Peut aider a relancer son engagement en magasin.');
    }

    return reasons;
  }

  List<String> _normalizeCategories(List<String> categories) {
    return categories.map(_normalizeSingleCategory).toSet().toList();
  }

  String _normalizeSingleCategory(String value) {
    const mapping = {
      'electronics': 'computers_accessories',
      'accessories': 'watches_gifts',
      'beauty': 'health_beauty',
      'sports': 'sports_leisure',
      'furniture': 'furniture_decor',
      'home': 'housewares',
      'decor': 'furniture_decor',
      'kids': 'toys',
      'toys': 'toys',
      'phone': 'telephony',
      'phones': 'telephony',
      'auto': 'auto',
      'bed': 'bed_bath_table',
      'bath': 'bed_bath_table',
    };

    final normalized = value.toLowerCase().trim();
    for (final entry in mapping.entries) {
      if (normalized == entry.key || normalized.contains(entry.key)) {
        return entry.value;
      }
    }
    return normalized.replaceAll(' ', '_');
  }

  Widget _buildCustomerProfileCard(BuildContext context) {
    final hasProfile = _segmentLabel != null && _churnRisk != null;
    final rawRisk = _churnRisk ?? 0;
    final displayRisk = _displayChurnRisk(rawRisk);
    final riskColor = _getRiskColor(displayRisk);

    return Card(
      elevation: 2,
      shadowColor: Colors.black26,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Fiche client',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _businessField(
                  _recencyController,
                  'Jours depuis dernier achat',
                ),
                _businessField(_frequencyController, 'Nombre d\'achats'),
                _businessField(_monetaryController, 'Depense cumulee'),
                _businessField(_priceController, 'Panier actuel'),
                _businessField(_categoryController, 'Categorie principale'),
                _businessField(_paymentTypeController, 'Mode de paiement'),
                _businessField(_stateController, 'Region client'),
              ],
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _categoriesController,
              decoration: const InputDecoration(
                labelText:
                    'Achats/categories recents (separes par des virgules)',
                border: OutlineInputBorder(),
              ),
            ),
            if (_loading) ...[const SizedBox(height: 14), _buildProgressCard()],
            if (hasProfile) ...[
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: riskColor.withOpacity(0.08),
                  border: Border.all(color: riskColor.withOpacity(0.35)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Client',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Profil client: ${_segmentLabel ?? 'Profil non disponible'}',
                    ),
                    const SizedBox(height: 4),
                    Text(_segmentDescription ?? ''),
                    const SizedBox(height: 4),
                    Text(
                      'Risque de depart client (API): ${_riskLevel ?? getRiskLevel(displayRisk)}',
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Score interprete (affichage): ${(displayRisk * 100).toStringAsFixed(1)} %',
                      style: TextStyle(
                        color: riskColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Score brut modele: ${(rawRisk * 100).toStringAsFixed(1)} %',
                      style: TextStyle(
                        color: riskColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      'Conseils IA',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text(_churnMessage ?? ''),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestedActionsCard() {
    final segment = _clusterId;
    final risk = _churnRisk;

    return Card(
      elevation: 2,
      shadowColor: Colors.black26,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Actions suggerees',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            if (segment == null || risk == null)
              const Text(
                'Generez d\'abord les recommandations pour afficher les actions prioritaires.',
              )
            else
              ..._getSuggestedActions(segment: segment, risk: risk).map(
                (action) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 2),
                        child: Icon(Icons.check_circle, size: 16),
                      ),
                      const SizedBox(width: 8),
                      Expanded(child: Text(action)),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationsCard() {
    return Card(
      elevation: 2,
      shadowColor: Colors.black26,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Produits recommandes',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            if (_items.isEmpty)
              const Text(
                'Aucune recommandation pour le moment. Lancez une analyse client.',
              )
            else
              ..._items.map((item) {
                final productName = _formatProductName(item);
                final reasons = _buildReasonsForProduct();

                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    color: Colors.white,
                    border: Border.all(color: const Color(0xFFE3E8EA)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: const Color(0xFFE6F4F3),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Icon(
                              Icons.shopping_cart,
                              color: Color(0xFF0A7F78),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              productName,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Produit pertinent pour ce client et son historique d\'achat.',
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Recommandee car :',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 4),
                      ...reasons.map(
                        (reason) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Text('• $reason'),
                        ),
                      ),
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: const Color(0xFFF2F7F7),
        border: Border.all(color: const Color(0xFFD5E6E4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Analyse du profil...',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          _buildProgressStep('Segmentation', stepNumber: 1),
          _buildProgressStep('Analyse du churn', stepNumber: 2),
          _buildProgressStep('Generation des recommandations', stepNumber: 3),
        ],
      ),
    );
  }

  Widget _buildProgressStep(String label, {required int stepNumber}) {
    final isDone = _progressStep >= stepNumber;
    final isCurrent = _loading && _progressStep == stepNumber - 1;

    IconData icon;
    Color color;
    String prefix;

    if (isDone) {
      icon = Icons.check_circle;
      color = const Color(0xFF2E7D32);
      prefix = '✔';
    } else if (isCurrent) {
      icon = Icons.hourglass_top;
      color = const Color(0xFFF9A825);
      prefix = '⏳';
    } else {
      icon = Icons.radio_button_unchecked;
      color = Colors.grey;
      prefix = '•';
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '$prefix $label',
              style: TextStyle(color: color, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          'Recommandation client',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 6),
        const Text(
          'Assistant intelligent pour conseiller les produits en magasin selon le profil client.',
        ),
        const SizedBox(height: 14),
        _buildCustomerProfileCard(context),
        const SizedBox(height: 12),
        _buildSuggestedActionsCard(),
        const SizedBox(height: 12),
        _buildRecommendationsCard(),
        const SizedBox(height: 14),
        FilledButton.icon(
          onPressed: _loading ? null : _runRecommendations,
          icon: const Icon(Icons.recommend),
          label: Text(_loading ? 'Chargement...' : 'Generer recommandations'),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFFFEBEE),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFFFCDD2)),
            ),
            child: Text(
              _error!,
              style: const TextStyle(color: Color(0xFFC62828)),
            ),
          ),
        ],
      ],
    );
  }

  Widget _businessField(TextEditingController controller, String label) {
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
