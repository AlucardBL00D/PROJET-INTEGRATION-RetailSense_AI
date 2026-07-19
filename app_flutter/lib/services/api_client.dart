import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ApiClient {
  static const int _defaultRecommendationsTopK = 5;

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
    required double recency,
    required double frequency,
    required double monetary,
    required List<String> recentCategories,
  }) async {
    final now = DateTime.now();
    final nItems = recentCategories.isEmpty ? 1 : recentCategories.length;

    final maxInstallments = switch (paymentType.toLowerCase()) {
      'credit_card' => 6,
      'debit_card' => 2,
      'boleto' => 1,
      'voucher' => 1,
      _ => 3,
    };

    final totalFreight = (totalPrice * 0.08).clamp(2.0, 120.0).toDouble();
    final totalWeight = (0.35 * nItems + (monetary / 400.0))
        .clamp(0.2, 30.0)
        .toDouble();
    final deliveryDays = (3 + (recency / 120.0)).clamp(2.0, 10.0).round();
    final delayDays = ((recency > 260 ? 2 : 0) + (frequency <= 1 ? 1 : 0))
        .clamp(0, 5);

    return _post('/predict/churn', {
      'total_price': totalPrice,
      'total_freight': totalFreight,
      'total_weight': totalWeight,
      'n_items': nItems,
      'max_installments': maxInstallments,
      'payment_value': totalPrice,
      'delivery_days': deliveryDays,
      'delay_days': delayDays,
      'purchase_month': now.month,
      'purchase_dow': now.weekday % 7,
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
  }) async {
    final payload = {
      'segment': segment,
      'churn_risk': churnRisk,
      'recent_categories': recentCategories,
      'top_k': _defaultRecommendationsTopK,
    };

    try {
      return await _post('/recommend/products', payload);
    } on ApiException catch (exc) {
      // Compatibility fallback for older deployments.
      if (exc.statusCode == 404) {
        return _post('/predict/recommendations', payload);
      }
      rethrow;
    }
  }

  Future<Map<String, dynamic>> predictAnomaly({
    required double totalPrice,
    required double totalFreight,
    required double totalWeight,
    required double nItems,
    required double maxInstallments,
    required double paymentValue,
    required double deliveryDays,
    required double delayDays,
  }) async {
    return _post('/predict/anomaly', {
      'total_price': totalPrice,
      'total_freight': totalFreight,
      'total_weight': totalWeight,
      'n_items': nItems,
      'max_installments': maxInstallments,
      'payment_value': paymentValue,
      'delivery_days': deliveryDays,
      'delay_days': delayDays,
    });
  }

  Future<Map<String, dynamic>> _get(String path) async {
    try {
      final response = await _http
          .get(_uri(path))
          .timeout(const Duration(seconds: 8));
      return _decode(response);
    } on ApiException {
      rethrow;
    } catch (exc) {
      throw ApiException('Network error: $exc');
    }
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> payload,
  ) async {
    try {
      if (kDebugMode) {
        debugPrint('[ApiClient] POST $path payload=$payload');
      }
      final response = await _http
          .post(
            _uri(path),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 12));
      final decoded = _decode(response);
      if (kDebugMode) {
        debugPrint('[ApiClient] POST $path response=$decoded');
      }
      return decoded;
    } on ApiException {
      rethrow;
    } catch (exc) {
      if (kDebugMode) {
        debugPrint('[ApiClient] POST $path error=$exc');
      }
      throw ApiException('Network error: $exc');
    }
  }

  Map<String, dynamic> _decode(http.Response response) {
    final body = response.body;
    Map<String, dynamic>? decoded;

    if (body.isNotEmpty) {
      try {
        final parsed = jsonDecode(body);
        if (parsed is Map<String, dynamic>) {
          decoded = parsed;
        }
      } on FormatException {
        decoded = null;
      }
    }

    if (response.statusCode >= 400) {
      final detail = decoded?['detail']?.toString();
      final fallback = body.trim().isEmpty
          ? 'HTTP ${response.statusCode}'
          : body.trim().replaceAll(RegExp(r'\s+'), ' ');
      throw ApiException(
        detail == null || detail.isEmpty ? fallback : detail,
        statusCode: response.statusCode,
      );
    }

    if (decoded == null) {
      throw ApiException(
        'Invalid API response format (status ${response.statusCode})',
        statusCode: response.statusCode,
      );
    }

    return decoded;
  }
}
