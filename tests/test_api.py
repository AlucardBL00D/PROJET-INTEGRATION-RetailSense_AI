from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_churn_prediction_endpoint():
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


def test_segmentation_endpoint():
    response = client.post(
        "/predict/segmentation",
        json={"recency": 0.2, "frequency": 0.8, "monetary": 0.6},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cluster" in data
    assert isinstance(data["cluster"], int)


def test_sentiment_endpoint():
    response = client.post(
        "/predict/sentiment",
        json={"text": "Excellent delivery and very satisfied with the service"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["label"] in {"positive", "neutral", "negative"}
