import 'package:flutter/material.dart';

import 'config/api_config.dart';
import 'screens/client_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/forecast_screen.dart';
import 'screens/login_screen.dart';
import 'screens/recommendations_screen.dart';
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
    final pages = [
      DashboardScreen(apiClient: widget.apiClient),
      ClientScreen(apiClient: widget.apiClient),
      ForecastScreen(apiClient: widget.apiClient),
      RecommendationsScreen(apiClient: widget.apiClient),
    ];

    final destinations = const [
      NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dashboard'),
      NavigationDestination(icon: Icon(Icons.person), label: 'Client'),
      NavigationDestination(icon: Icon(Icons.trending_up), label: 'Demande'),
      NavigationDestination(
        icon: Icon(Icons.recommend),
        label: 'Reco/Anomalie',
      ),
    ];

    final wide = MediaQuery.of(context).size.width >= 980;

    return Scaffold(
      appBar: AppBar(
        title: const Text('RetailSense AI'),
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
      body: Row(
        children: [
          if (wide)
            NavigationRail(
              selectedIndex: _index,
              onDestinationSelected: (value) => setState(() => _index = value),
              labelType: NavigationRailLabelType.all,
              destinations: const [
                NavigationRailDestination(
                  icon: Icon(Icons.dashboard),
                  label: Text('Dashboard'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.person),
                  label: Text('Client'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.trending_up),
                  label: Text('Demande'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.recommend),
                  label: Text('Reco/Anomalie'),
                ),
              ],
            ),
          Expanded(child: pages[_index]),
        ],
      ),
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: _index,
              destinations: destinations,
              onDestinationSelected: (value) => setState(() => _index = value),
            ),
    );
  }
}
