from pathlib import Path

import joblib
import pytest
from fastapi.testclient import TestClient

from api import main as api_main
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


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["docs"] == "/docs"


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
        json={"recency": 250, "frequency": 2, "monetary": 450},
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


def test_sentiment_negative_endpoint() -> None:
    response = client.post(
        "/predict/sentiment",
        json={"text": "Livraison en retard, produit mauvais et je suis tres decu"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "negative"


def test_anomaly_endpoint_rejects_feature_size_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeScaler:
        n_features_in_ = 4

        def transform(self, x):  # pragma: no cover
            return x

    monkeypatch.setitem(api_main.MODEL_CACHE, "autoencoder_scaler.joblib", _FakeScaler())
    response = client.post("/predict/anomaly", json={"features": [0.0, 0.1, 0.2]})
    assert response.status_code == 422
    payload = response.json()
    assert "Expected 4 features" in payload["detail"]


def test_demand_endpoint_rejects_short_input() -> None:
    response = client.post(
        "/predict/demand",
        json={"recent_daily_orders": [10, 11, 12, 13, 14, 15], "horizon_days": 7},
    )
    assert response.status_code == 422
