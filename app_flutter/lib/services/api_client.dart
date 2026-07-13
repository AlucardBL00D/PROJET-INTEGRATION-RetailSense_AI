import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ApiClient {
  final String baseUrl;
  final http.Client _http;

  ApiClient({required this.baseUrl, http.Client? httpClient})
    : _http = httpClient ?? http.Client();

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> health() async => _get('/health');

  Future<Map<String, dynamic>> predictSegmentation({
    required double recency,
    required double frequency,
    required double monetary,
  }) async {
    return _post('/predict/segmentation', {
      'recency': recency,
      'frequency': frequency,
      'monetary': monetary,
    });
  }

  Future<Map<String, dynamic>> predictChurn({
    required double totalPrice,
    required String category,
    required String paymentType,
    required String customerState,
  }) async {
    return _post('/predict/churn', {
      'total_price': totalPrice,
      'total_freight': 12.5,
      'total_weight': 2.1,
      'n_items': 3,
      'max_installments': 3,
      'payment_value': totalPrice,
      'delivery_days': 4,
      'delay_days': 0,
      'purchase_month': 7,
      'purchase_dow': 4,
      'main_category': category,
      'payment_type': paymentType,
      'customer_state': customerState,
    });
  }

  Future<Map<String, dynamic>> predictSentiment(String text) async {
    return _post('/predict/sentiment', {'text': text});
  }

  Future<Map<String, dynamic>> predictDemand({
    required List<double> recentDailyOrders,
    required int horizonDays,
  }) async {
    return _post('/predict/demand', {
      'recent_daily_orders': recentDailyOrders,
      'horizon_days': horizonDays,
    });
  }

  Future<Map<String, dynamic>> predictRecommendations({
    required int segment,
    required double churnRisk,
    required List<String> recentCategories,
    required int topK,
  }) async {
    return _post('/predict/recommendations', {
      'segment': segment,
      'churn_risk': churnRisk,
      'recent_categories': recentCategories,
      'top_k': topK,
    });
  }

  Future<Map<String, dynamic>> predictAnomaly(List<double> features) async {
    return _post('/predict/anomaly', {'features': features});
  }

  Future<Map<String, dynamic>> _get(String path) async {
    try {
      final response = await _http
          .get(_uri(path))
          .timeout(const Duration(seconds: 8));
      return _decode(response);
    } catch (exc) {
      throw ApiException('Network error: $exc');
    }
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> payload,
  ) async {
    try {
      final response = await _http
          .post(
            _uri(path),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 12));
      return _decode(response);
    } catch (exc) {
      throw ApiException('Network error: $exc');
    }
  }

  Map<String, dynamic> _decode(http.Response response) {
    final body = response.body.isEmpty ? '{}' : response.body;
    final decoded = jsonDecode(body);
    if (decoded is! Map<String, dynamic>) {
      throw ApiException(
        'Invalid API response format',
        statusCode: response.statusCode,
      );
    }
    if (response.statusCode >= 400) {
      final detail = decoded['detail'] ?? 'HTTP ${response.statusCode}';
      throw ApiException(detail.toString(), statusCode: response.statusCode);
    }
    return decoded;
  }
}
