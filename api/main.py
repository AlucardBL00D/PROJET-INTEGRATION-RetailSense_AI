from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"

app = FastAPI(title="RetailSenseAI API", version="1.0.0")


class ChurnRequest(BaseModel):
    total_price: float = Field(..., gt=0)
    total_freight: float = Field(..., ge=0)
    total_weight: float = Field(..., ge=0)
    n_items: int = Field(..., ge=1)
    max_installments: int = Field(..., ge=1)
    payment_value: float = Field(..., gt=0)
    delivery_days: int = Field(..., ge=0)
    delay_days: int = Field(..., ge=0)
    purchase_month: int = Field(..., ge=1, le=12)
    purchase_dow: int = Field(..., ge=0, le=6)
    main_category: str
    payment_type: str
    customer_state: str


class ChurnResponse(BaseModel):
    prediction: int
    risk_probability: float
    model: str = "churn_best"


class SegmentationRequest(BaseModel):
    recency: float = Field(..., ge=0, le=1)
    frequency: float = Field(..., ge=0, le=1)
    monetary: float = Field(..., ge=0, le=1)


class SegmentationResponse(BaseModel):
    cluster: int
    model: str = "kmeans_rfm"


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1)


class SentimentResponse(BaseModel):
    label: str
    confidence: float


class HealthResponse(BaseModel):
    status: str
    models_loaded: List[str]


MODEL_CACHE: Dict[str, Any] = {}


def load_model(name: str) -> Any:
    if name not in MODEL_CACHE:
        path = MODELS_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        MODEL_CACHE[name] = joblib.load(path)
    return MODEL_CACHE[name]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    available = []
    for name in ["churn_best.joblib", "kmeans_rfm.joblib", "delivery_best.joblib"]:
        if (MODELS_DIR / name).exists():
            available.append(name)
    return HealthResponse(status="ok", models_loaded=available)


@app.post("/predict/churn", response_model=ChurnResponse)
def predict_churn(payload: ChurnRequest) -> ChurnResponse:
    try:
        model = load_model("churn_best.joblib")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    row = pd.DataFrame([payload.model_dump()])
    probability = float(model.predict_proba(row)[0, 1])
    prediction = int(probability >= 0.5)
    return ChurnResponse(prediction=prediction, risk_probability=probability)


@app.post("/predict/segmentation", response_model=SegmentationResponse)
def predict_segmentation(payload: SegmentationRequest) -> SegmentationResponse:
    try:
        model = load_model("kmeans_rfm.joblib")
    except FileNotFoundError:
        return SegmentationResponse(cluster=0)

    features = np.array([[payload.recency, payload.frequency, payload.monetary]], dtype=float)
    cluster = int(model.predict(features)[0])
    return SegmentationResponse(cluster=cluster)


@app.post("/predict/sentiment", response_model=SentimentResponse)
def predict_sentiment(payload: SentimentRequest) -> SentimentResponse:
    text = payload.text.lower()
    positive_words = ["excellent", "good", "great", "love", "satisfied", "happy", "fast", "thanks"]
    negative_words = ["bad", "terrible", "poor", "late", "angry", "disappointed", "issue", "problem"]

    pos_count = sum(1 for word in positive_words if word in text)
    neg_count = sum(1 for word in negative_words if word in text)

    if pos_count > neg_count:
        return SentimentResponse(label="positive", confidence=min(0.99, 0.6 + 0.1 * pos_count))
    if neg_count > pos_count:
        return SentimentResponse(label="negative", confidence=min(0.99, 0.6 + 0.1 * neg_count))
    return SentimentResponse(label="neutral", confidence=0.6)


@app.get("/predict/delivery")
def delivery_demo() -> Dict[str, Any]:
    return {
        "message": "Delivery endpoint ready",
        "model": "delivery_best.joblib",
        "status": "available" if (MODELS_DIR / "delivery_best.joblib").exists() else "missing",
    }
