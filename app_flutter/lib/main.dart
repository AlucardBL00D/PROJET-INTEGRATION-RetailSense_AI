import 'dart:convert';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const RetailSenseApp());
}

class RetailSenseApp extends StatelessWidget {
  const RetailSenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RetailSense AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: const AuthGate(),
    );
  }
}

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool _loggedIn = false;

  void _handleLogin() {
    setState(() {
      _loggedIn = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loggedIn) {
      return const HomeScreen();
    }
    return LoginScreen(onLogin: _handleLogin);
  }
}

class LoginScreen extends StatefulWidget {
  final VoidCallback onLogin;
  const LoginScreen({super.key, required this.onLogin});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController(
    text: 'ops@retailsense.ai',
  );
  final TextEditingController _passwordController = TextEditingController(
    text: 'retailsense',
  );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          margin: const EdgeInsets.all(24),
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: Colors.black12,
                blurRadius: 20,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'RetailSense AI',
                  style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Connexion à votre espace décisionnel',
                  style: TextStyle(color: Colors.black54),
                ),
                const SizedBox(height: 24),
                TextFormField(
                  controller: _emailController,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) =>
                      value!.contains('@') ? null : 'Email invalide',
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Mot de passe',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) =>
                      value!.length >= 4 ? null : 'Mot de passe trop court',
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {
                      if (_formKey.currentState!.validate()) {
                        widget.onLogin();
                      }
                    },
                    icon: const Icon(Icons.login),
                    label: const Text('Se connecter'),
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Démo : ops@retailsense.ai / retailsense',
                  style: TextStyle(fontSize: 12, color: Colors.black54),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  bool _loading = true;
  String _status = 'Chargement...';

  final List<Widget> _pages = [
    const DashboardPage(),
    const ClientPage(),
    const ForecastPage(),
    const InsightsPage(),
    const SettingsPage(),
  ];

  Future<void> _checkApi() async {
    try {
      final response = await http
          .get(Uri.parse('http://127.0.0.1:8000/health'))
          .timeout(const Duration(seconds: 5));
      setState(() {
        _status = response.statusCode == 200
            ? 'API connectée'
            : 'API indisponible';
        _loading = false;
      });
    } catch (_) {
      setState(() {
        _status = 'Connexion impossible';
        _loading = false;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _checkApi();
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width >= 900;

    return Scaffold(
      appBar: AppBar(
        title: const Text('RetailSense AI'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(child: Text(_status)),
          ),
        ],
      ),
      drawer: isWide
          ? null
          : Drawer(
              child: ListView(
                children: [
                  const DrawerHeader(
                    child: Text(
                      'Navigation',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  _drawerTile(0, Icons.dashboard, 'Tableau de bord'),
                  _drawerTile(1, Icons.person, 'Client'),
                  _drawerTile(2, Icons.insights, 'Prévisions'),
                  _drawerTile(3, Icons.auto_graph, 'Insights'),
                  _drawerTile(4, Icons.settings, 'Paramètres'),
                ],
              ),
            ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Row(
              children: [
                if (isWide)
                  NavigationRail(
                    selectedIndex: _selectedIndex,
                    onDestinationSelected: (index) =>
                        setState(() => _selectedIndex = index),
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
                        icon: Icon(Icons.insights),
                        label: Text('Prévision'),
                      ),
                      NavigationRailDestination(
                        icon: Icon(Icons.auto_graph),
                        label: Text('Insights'),
                      ),
                      NavigationRailDestination(
                        icon: Icon(Icons.settings),
                        label: Text('Paramètres'),
                      ),
                    ],
                  ),
                Expanded(child: _pages[_selectedIndex]),
              ],
            ),
      bottomNavigationBar: isWide
          ? null
          : NavigationBar(
              selectedIndex: _selectedIndex,
              onDestinationSelected: (index) =>
                  setState(() => _selectedIndex = index),
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.dashboard),
                  label: 'Dashboard',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person),
                  label: 'Client',
                ),
                NavigationDestination(
                  icon: Icon(Icons.insights),
                  label: 'Prévision',
                ),
              ],
            ),
    );
  }

  Widget _drawerTile(int index, IconData icon, String title) {
    return ListTile(
      leading: Icon(icon),
      title: Text(title),
      selected: _selectedIndex == index,
      onTap: () {
        setState(() => _selectedIndex = index);
        Navigator.pop(context);
      },
    );
  }
}

class DashboardPage extends StatelessWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Vue d’ensemble',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Supervision des indicateurs métiers et des prédictions IA en un seul endroit.',
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: const [
                    _MetricChip(label: 'Taux de churn', value: '12.4%'),
                    _MetricChip(label: 'Segmentation', value: '4 clusters'),
                    _MetricChip(label: 'Demande', value: '+8%'),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, constraints) {
            final wide = constraints.maxWidth > 700;
            return Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                SizedBox(
                  width: wide
                      ? constraints.maxWidth / 2 - 8
                      : constraints.maxWidth,
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: SizedBox(height: 240, child: _buildLineChart()),
                    ),
                  ),
                ),
                SizedBox(
                  width: wide
                      ? constraints.maxWidth / 2 - 8
                      : constraints.maxWidth,
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: SizedBox(height: 240, child: _buildBarChart()),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 20),
        const Text(
          'Actions rapides',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: const [
            _ActionTile(
              title: 'Client',
              subtitle: 'Fiche client',
              icon: Icons.person_outline,
            ),
            _ActionTile(
              title: 'Prévision',
              subtitle: 'Demande',
              icon: Icons.auto_graph,
            ),
            _ActionTile(
              title: 'Insights',
              subtitle: 'Analyse IA',
              icon: Icons.insights,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildLineChart() {
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: const [
              FlSpot(0, 1.5),
              FlSpot(1, 2.4),
              FlSpot(2, 2.2),
              FlSpot(3, 3.1),
              FlSpot(4, 2.8),
              FlSpot(5, 3.5),
            ],
            isCurved: true,
            color: Colors.indigo,
            barWidth: 3,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _buildBarChart() {
    return BarChart(
      BarChartData(
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(show: false),
        barGroups: [
          BarChartGroupData(
            x: 0,
            barRods: [BarChartRodData(toY: 4, color: Colors.indigo, width: 16)],
          ),
          BarChartGroupData(
            x: 1,
            barRods: [BarChartRodData(toY: 5, color: Colors.teal, width: 16)],
          ),
          BarChartGroupData(
            x: 2,
            barRods: [BarChartRodData(toY: 3, color: Colors.orange, width: 16)],
          ),
          BarChartGroupData(
            x: 3,
            barRods: [BarChartRodData(toY: 6, color: Colors.pink, width: 16)],
          ),
        ],
      ),
    );
  }
}

class ClientPage extends StatefulWidget {
  const ClientPage({super.key});

  @override
  State<ClientPage> createState() => _ClientPageState();
}

class _ClientPageState extends State<ClientPage> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _recencyController = TextEditingController(
    text: '0.2',
  );
  final TextEditingController _frequencyController = TextEditingController(
    text: '0.8',
  );
  final TextEditingController _monetaryController = TextEditingController(
    text: '0.6',
  );
  final TextEditingController _churnPriceController = TextEditingController(
    text: '150',
  );
  final TextEditingController _churnTextController = TextEditingController(
    text: 'Excellent service',
  );

  Map<String, dynamic>? _segmentation;
  Map<String, dynamic>? _churn;
  Map<String, dynamic>? _sentiment;
  bool _loading = false;

  Future<void> _callApis() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);

    try {
      final segRes = await http.post(
        Uri.parse('http://127.0.0.1:8000/predict/segmentation'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'recency': double.parse(_recencyController.text),
          'frequency': double.parse(_frequencyController.text),
          'monetary': double.parse(_monetaryController.text),
        }),
      );

      final churnRes = await http.post(
        Uri.parse('http://127.0.0.1:8000/predict/churn'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'total_price': double.parse(_churnPriceController.text),
          'total_freight': 12.5,
          'total_weight': 2.1,
          'n_items': 3,
          'max_installments': 3,
          'payment_value': double.parse(_churnPriceController.text),
          'delivery_days': 4,
          'delay_days': 0,
          'purchase_month': 7,
          'purchase_dow': 4,
          'main_category': 'electronics',
          'payment_type': 'credit_card',
          'customer_state': 'SP',
        }),
      );

      final sentimentRes = await http.post(
        Uri.parse('http://127.0.0.1:8000/predict/sentiment'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': _churnTextController.text}),
      );

      setState(() {
        _segmentation = jsonDecode(segRes.body);
        _churn = jsonDecode(churnRes.body);
        _sentiment = jsonDecode(sentimentRes.body);
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
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
            const Text(
              'Fiche client',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              'Analysez le profil du client à partir des services IA.',
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                SizedBox(
                  width: 320,
                  child: Column(
                    children: [
                      TextFormField(
                        controller: _recencyController,
                        decoration: const InputDecoration(
                          labelText: 'Recency',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (v) => v!.isEmpty ? 'Obligatoire' : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _frequencyController,
                        decoration: const InputDecoration(
                          labelText: 'Frequency',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (v) => v!.isEmpty ? 'Obligatoire' : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _monetaryController,
                        decoration: const InputDecoration(
                          labelText: 'Monetary',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (v) => v!.isEmpty ? 'Obligatoire' : null,
                      ),
                    ],
                  ),
                ),
                SizedBox(
                  width: 320,
                  child: Column(
                    children: [
                      TextFormField(
                        controller: _churnPriceController,
                        decoration: const InputDecoration(
                          labelText: 'Valeur panier',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (v) => v!.isEmpty ? 'Obligatoire' : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _churnTextController,
                        decoration: const InputDecoration(
                          labelText: 'Avis client',
                          border: OutlineInputBorder(),
                        ),
                        validator: (v) => v!.isEmpty ? 'Obligatoire' : null,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loading ? null : _callApis,
              icon: const Icon(Icons.analytics),
              label: _loading
                  ? const Text('Analyse en cours...')
                  : const Text('Analyser le client'),
            ),
            const SizedBox(height: 16),
            if (_segmentation != null)
              _InfoCard(
                title: 'Segmentation',
                value: 'Cluster ${_segmentation!['cluster']}',
              ),
            if (_churn != null)
              _InfoCard(
                title: 'Risque churn',
                value:
                    'Probabilité ${(_churn!['risk_probability'] * 100).toStringAsFixed(1)}%',
              ),
            if (_sentiment != null)
              _InfoCard(
                title: 'Sentiment',
                value: _sentiment!['label'].toUpperCase(),
              ),
          ],
        ),
      ),
    );
  }
}

class ForecastPage extends StatelessWidget {
  const ForecastPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Prévision de demande',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          const Text(
            'Visualisez la tendance de demande et les produits à promouvoir.',
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.trending_up),
              title: const Text('Demande attendue'),
              subtitle: const Text('Hausse de 8% sur les prochains 7 jours'),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: const Icon(Icons.recommend),
              title: const Text('Recommandations produits'),
              subtitle: const Text(
                'Électronique, accessoires, produits premium',
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: const Icon(Icons.inventory_2),
              title: const Text('Stocks stratégiques'),
              subtitle: const Text('Prioriser les produits à reconstituer'),
            ),
          ),
        ],
      ),
    );
  }
}

class InsightsPage extends StatelessWidget {
  const InsightsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Insights IA',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          const Text(
            'Synthèse automatique des signaux générés par les modèles.',
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              title: const Text('Signal principal'),
              subtitle: const Text(
                'Le risque de churn est plus élevé sur les clients ayant un faible panier et un avis négatif.',
              ),
            ),
          ),
          Card(
            child: ListTile(
              title: const Text('Opportunité'),
              subtitle: const Text(
                'Le segment premium montre une forte propension à acheter des accessoires.',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Paramètres',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          const Text(
            'Préférences de l’application et configuration de connexion.',
          ),
          const SizedBox(height: 16),
          SwitchListTile(
            value: true,
            onChanged: (_) {},
            title: const Text('Notifications IA'),
          ),
          SwitchListTile(
            value: true,
            onChanged: (_) {},
            title: const Text('Mode sombre'),
          ),
        ],
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  final String label;
  final String value;
  const _MetricChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text('$label: $value'));
  }
}

class _ActionTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  const _ActionTile({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        width: 180,
        child: ListTile(
          leading: Icon(icon),
          title: Text(title),
          subtitle: Text(subtitle),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final String title;
  final String value;
  const _InfoCard({required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(title: Text(title), subtitle: Text(value)),
    );
  }
}
