import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/screen_intro_card.dart';

class DashboardScreen extends StatefulWidget {
  final ApiClient apiClient;

  const DashboardScreen({super.key, required this.apiClient});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _loading = true;
  String _status = 'Connexion...';
  List<String> _models = const [];

  @override
  void initState() {
    super.initState();
    _loadHealth();
  }

  Future<void> _loadHealth() async {
    setState(() => _loading = true);
    try {
      final health = await widget.apiClient.health();
      final models = (health['models_loaded'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList();
      setState(() {
        _status = health['status']?.toString() ?? 'unknown';
        _models = models;
        _loading = false;
      });
    } catch (exc) {
      setState(() {
        _status = exc.toString();
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
          'Tableau de bord',
          style: Theme.of(
            context,
          ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text('Etat API: $_status'),
        const SizedBox(height: 16),
        const ScreenIntroCard(
          title: 'Ce que cette section montre',
          description:
              'Vue executive de la plateforme: disponibilite du service, modeles charges et cas d\'usage metier disponibles.',
          bullets: [
            'Verifier rapidement que la plateforme est operationnelle.',
            'Presenter les capacites IA actives a un client.',
            'Servir de page de depart avant une demo detaillee.',
          ],
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: _loading
                ? const SizedBox(
                    height: 120,
                    child: Center(child: CircularProgressIndicator()),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Modeles charges',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _models
                            .map(
                              (model) => Chip(
                                label: Text(model),
                                avatar: const Icon(Icons.memory),
                              ),
                            )
                            .toList(),
                      ),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: SizedBox(height: 220, child: _buildTrendChart()),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Services IA que vous pouvez proposer',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 10),
        const _ServiceTile(
          icon: Icons.trending_up,
          title: 'Prevision de la demande',
          subtitle:
              'Projection des commandes a court terme pour planifier stock et equipe.',
        ),
        const _ServiceTile(
          icon: Icons.recommend,
          title: 'Recommendations personnalisees',
          subtitle:
              'Fiche client claire, actions suggerees et produits recommandes avec explications metier.',
        ),
        const _ServiceTile(
          icon: Icons.shield,
          title: 'Surveillance d\'anomalies',
          subtitle:
              'Detection d\'activites atypiques ou suspectes en quasi temps reel.',
        ),
        const _ServiceTile(
          icon: Icons.person_search,
          title: 'Sentiment d\'un avis',
          subtitle: 'Analyser le ton des avis pour mesurer la satisfaction client',
        ),
      ],
    );
  }

  Widget _buildTrendChart() {
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: const [
              FlSpot(0, 14),
              FlSpot(1, 17),
              FlSpot(2, 16),
              FlSpot(3, 19),
              FlSpot(4, 20),
              FlSpot(5, 23),
              FlSpot(6, 22),
            ],
            isCurved: true,
            color: const Color(0xFF1E847F),
            barWidth: 3,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }
}

class _ServiceTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _ServiceTile({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: Text(subtitle),
      ),
    );
  }
}
