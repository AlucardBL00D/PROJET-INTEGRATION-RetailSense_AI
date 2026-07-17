#!/usr/bin/env python3
"""Quick test of API endpoints without pytest overhead."""

import sys
import json
from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_endpoint(name: str, method: str, path: str, json_data: dict = None):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    try:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json=json_data)
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print("✓ PASSED")
            return True
        else:
            print(f"Error: {resp.text}")
            print("✗ FAILED")
            return False
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test endpoints
results = {}

results["health"] = test_endpoint(
    "Health", "GET", "/health"
)

results["churn"] = test_endpoint(
    "Churn Prediction",
    "POST",
    "/predict/churn",
    {
        "total_price": 150.0,
        "total_freight": 12.5,
        "total_weight": 2.1,
        "n_items": 3,
        "max_installments": 3,
        "payment_value": 162.5,
        "delivery_days": 4,
        "delay_days": 0,
        "purchase_month": 7,
        "purchase_dow": 4,
        "main_category": "electronics",
        "payment_type": "credit_card",
        "customer_state": "SP",
    }
)

results["segmentation"] = test_endpoint(
    "Segmentation",
    "POST",
    "/predict/segmentation",
    {"recency": 250, "frequency": 2, "monetary": 450}
)

results["demand"] = test_endpoint(
    "Demand Forecast",
    "POST",
    "/predict/demand",
    {"recent_daily_orders": [18, 20, 17, 23, 22, 26, 29, 24], "horizon_days": 7}
)

results["sentiment"] = test_endpoint(
    "Sentiment (Positive)",
    "POST",
    "/predict/sentiment",
    {"text": "Excellent delivery and very satisfied with the service"}
)

results["sentiment_negative"] = test_endpoint(
    "Sentiment (Negative)",
    "POST",
    "/predict/sentiment",
    {"text": "Livraison en retard, produit mauvais et je suis tres decu"}
)

results["recommendations"] = test_endpoint(
    "Recommendations",
    "POST",
    "/predict/recommendations",
    {
        "customer_id": "CUST-001",
        "segment": 2,
        "churn_risk": 0.74,
        "recent_categories": ["electronics", "accessories"],
        "top_k": 5,
    }
)

results["anomaly"] = test_endpoint(
    "Anomaly Detection",
    "POST",
    "/predict/anomaly",
    {"features": [0.0] * 8}
)

# Summary
print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"Passed: {passed}/{total}")
for name, result in results.items():
    status = "✓" if result else "✗"
    print(f"  {status} {name}")

sys.exit(0 if passed == total else 1)
