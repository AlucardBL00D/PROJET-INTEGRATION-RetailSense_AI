import 'package:flutter/material.dart';

import 'config/api_config.dart';
import 'screens/anomaly_screen.dart';
import 'screens/churn_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/forecast_screen.dart';
import 'screens/login_screen.dart';
import 'screens/recommendations_screen.dart';
import 'screens/segmentation_screen.dart';
import 'screens/sentiment_screen.dart';
import 'services/api_client.dart';

class RetailSenseApp extends StatelessWidget {
  const RetailSenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RetailSense AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0A7F78)),
        scaffoldBackgroundColor: const Color(0xFFF5F7F7),
      ),
      home: const _AuthGate(),
    );
  }
}

class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  bool _loggedIn = false;
  late final ApiClient _apiClient;

  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient(baseUrl: ApiConfig.baseUrl);
  }

  @override
  Widget build(BuildContext context) {
    if (!_loggedIn) {
      return LoginScreen(
        onLogin: () {
          setState(() {
            _loggedIn = true;
          });
        },
      );
    }

    return _AppShell(apiClient: _apiClient);
  }
}

class _AppShell extends StatefulWidget {
  final ApiClient apiClient;

  const _AppShell({required this.apiClient});

  @override
  State<_AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<_AppShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final modules = [
      _Module(
        icon: Icons.dashboard,
        label: 'Vue globale',
        page: DashboardScreen(apiClient: widget.apiClient),
      ),
      _Module(
        icon: Icons.bubble_chart,
        label: 'Segmentation client',
        page: SegmentationScreen(apiClient: widget.apiClient),
      ),
      _Module(
        icon: Icons.person_off,
        label: 'Prediction churn',
        page: ChurnScreen(apiClient: widget.apiClient),
      ),
      _Module(
        icon: Icons.trending_up,
        label: 'Prevision demande',
        page: ForecastScreen(apiClient: widget.apiClient),
      ),
      _Module(
        icon: Icons.recommend,
        label: 'Recommandations',
        page: RecommendationsScreen(apiClient: widget.apiClient),
      ),
      _Module(
        icon: Icons.warning_amber,
        label: 'Score anomalie',
        page: AnomalyScreen(apiClient: widget.apiClient),
      ),
      _Module(
        icon: Icons.reviews,
        label: 'Sentiment avis',
        page: SentimentScreen(apiClient: widget.apiClient),
      ),
    ];

    final wide = MediaQuery.of(context).size.width >= 980;

    return Scaffold(
      appBar: AppBar(
        title: Text('RetailSense AI - ${modules[_index].label}'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                'API: ${ApiConfig.baseUrl}',
                style: const TextStyle(fontSize: 12),
              ),
            ),
          ),
        ],
      ),
      drawer: wide
          ? null
          : Drawer(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  const DrawerHeader(
                    decoration: BoxDecoration(color: Color(0xFF0A7F78)),
                    child: Align(
                      alignment: Alignment.bottomLeft,
                      child: Text(
                        'Modules RetailSense AI',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  ...List.generate(modules.length, (idx) {
                    final module = modules[idx];
                    return ListTile(
                      leading: Icon(module.icon),
                      title: Text(module.label),
                      selected: _index == idx,
                      onTap: () {
                        setState(() => _index = idx);
                        Navigator.of(context).pop();
                      },
                    );
                  }),
                ],
              ),
            ),
      body: Row(
        children: [
          if (wide)
            NavigationRail(
              selectedIndex: _index,
              onDestinationSelected: (value) => setState(() => _index = value),
              labelType: NavigationRailLabelType.all,
              destinations: modules
                  .map(
                    (module) => NavigationRailDestination(
                      icon: Icon(module.icon),
                      label: Text(module.label),
                    ),
                  )
                  .toList(),
            ),
          Expanded(child: modules[_index].page),
        ],
      ),
    );
  }
}

class _Module {
  final IconData icon;
  final String label;
  final Widget page;

  const _Module({required this.icon, required this.label, required this.page});
}
