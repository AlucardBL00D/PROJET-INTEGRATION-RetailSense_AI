from pathlib import Path

import joblib
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


def _build_anomaly_features() -> list[float]:
    scaler_path = MODELS_DIR / "autoencoder_scaler.joblib"
    if scaler_path.exists():
        scaler = joblib.load(scaler_path)
        expected = int(getattr(scaler, "n_features_in_", 8))
        return [0.0] * expected
    return [0.0] * 8


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "models_loaded" in payload
    assert "models_missing" in payload


def test_churn_prediction_endpoint() -> None:
    payload = {
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

    response = client.post("/predict/churn", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "risk_probability" in data
    assert 0.0 <= data["risk_probability"] <= 1.0


def test_segmentation_endpoint() -> None:
    response = client.post(
        "/predict/segmentation",
        json={"recency": 0.2, "frequency": 0.8, "monetary": 0.6},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cluster" in data
    assert isinstance(data["cluster"], int)


def test_demand_endpoint() -> None:
    response = client.post(
        "/predict/demand",
        json={"recent_daily_orders": [18, 20, 17, 23, 22, 26, 29, 24], "horizon_days": 7},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["horizon_days"] == 7
    assert len(data["forecast"]) == 7
    assert all(value >= 0 for value in data["forecast"])


def test_recommendations_endpoint() -> None:
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
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) == 5


def test_anomaly_endpoint() -> None:
    response = client.post("/predict/anomaly", json={"features": _build_anomaly_features()})
    assert response.status_code == 200
    data = response.json()
    assert data["anomaly_score"] >= 0
    assert isinstance(data["is_anomaly"], bool)


def test_sentiment_endpoint() -> None:
    response = client.post(
        "/predict/sentiment",
        json={"text": "Excellent delivery and very satisfied with the service"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] in {"positive", "neutral", "negative"}
