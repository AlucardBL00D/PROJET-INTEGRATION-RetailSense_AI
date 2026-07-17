#!/usr/bin/env python3
"""Test only the deep learning endpoints."""

import sys
import json
from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("\n" + "="*70)
print("TEST 1: Sentiment (Positive) - Transformer Model")
print("="*70)
try:
    resp = client.post(
        "/predict/sentiment",
        json={"text": "Excellent delivery and very satisfied with the service"}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"✓ Using model: {data.get('model')}")
    else:
        print(f"✗ Error: {resp.text}")
except Exception as e:
    print(f"✗ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST 2: Sentiment (Negative) - Transformer Model")
print("="*70)
try:
    resp = client.post(
        "/predict/sentiment",
        json={"text": "Livraison en retard, produit mauvais et je suis tres decu"}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"✓ Using model: {data.get('model')}")
    else:
        print(f"✗ Error: {resp.text}")
except Exception as e:
    print(f"✗ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST 3: Demand Forecast - RNN Model")
print("="*70)
try:
    resp = client.post(
        "/predict/demand",
        json={"recent_daily_orders": [18, 20, 17, 23, 22, 26, 29, 24], "horizon_days": 7}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"✓ Using model: {data.get('model')}")
    else:
        print(f"✗ Error: {resp.text}")
except Exception as e:
    print(f"✗ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST 4: Recommendations - GNN Model")
print("="*70)
try:
    resp = client.post(
        "/predict/recommendations",
        json={
            "customer_id": "CUST-001",
            "segment": 2,
            "churn_risk": 0.74,
            "recent_categories": ["electronics", "accessories"],
            "top_k": 5,
        }
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"✓ Using model: {data.get('model')}")
    else:
        print(f"✗ Error: {resp.text}")
except Exception as e:
    print(f"✗ Exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("DONE")
print("="*70)
