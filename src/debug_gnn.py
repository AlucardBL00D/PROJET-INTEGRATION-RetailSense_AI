#!/usr/bin/env python3
"""Debug GNN recommendations endpoint"""
import traceback
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

try:
    response = client.post(
        "/predict/recommendations",
        json={
            "customer_id": "CUST-001",
            "segment": 2,
            "churn_risk": 0.74,
            "recent_categories": ["electronics", "accessories"],
            "top_k": 5,
        },
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    traceback.print_exc()
