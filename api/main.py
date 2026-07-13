import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = Path(os.getenv("RETAILSENSE_MODELS_DIR", ROOT / "models"))
ANOMALY_THRESHOLD = float(os.getenv("RETAILSENSE_ANOMALY_THRESHOLD", "2.5"))

API_TITLE = "RetailSenseAI API"
API_VERSION = os.getenv("RETAILSENSE_API_VERSION", "1.1.0")

logger = logging.getLogger("retailsense.api")

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="REST API for RetailSenseAI model inference services.",
)

allowed_origins = os.getenv("RETAILSENSE_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    main_category: str = Field(..., min_length=1)
    payment_type: str = Field(..., min_length=1)
    customer_state: str = Field(..., min_length=1)


class ChurnResponse(BaseModel):
    prediction: int
    risk_probability: float
    model: str


class SegmentationRequest(BaseModel):
    recency: float = Field(..., ge=0, le=1)
    frequency: float = Field(..., ge=0, le=1)
    monetary: float = Field(..., ge=0, le=1)


class SegmentationResponse(BaseModel):
    cluster: int
    model: str


class DemandForecastRequest(BaseModel):
    recent_daily_orders: List[float] = Field(..., min_length=7, max_length=120)
    horizon_days: int = Field(7, ge=1, le=30)


class DemandForecastResponse(BaseModel):
    horizon_days: int
    forecast: List[float]
    model: str


class RecommendationRequest(BaseModel):
    customer_id: Optional[str] = None
    segment: Optional[int] = Field(default=None, ge=0, le=15)
    churn_risk: Optional[float] = Field(default=None, ge=0, le=1)
    recent_categories: List[str] = Field(default_factory=list)
    top_k: int = Field(5, ge=1, le=10)


class RecommendationResponse(BaseModel):
    recommendations: List[str]
    rationale: str
    model: str


class AnomalyRequest(BaseModel):
    features: List[float] = Field(..., min_length=3, max_length=256)


class AnomalyResponse(BaseModel):
    anomaly_score: float
    is_anomaly: bool
    threshold: float
    model: str


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class SentimentResponse(BaseModel):
    label: str
    confidence: float
    model: str


class HealthResponse(BaseModel):
    status: str
    api_version: str
    models_loaded: List[str]
    models_missing: List[str]


MODEL_CACHE: Dict[str, Any] = {}
MODEL_LOAD_ERRORS: Dict[str, str] = {}

CORE_MODEL_FILES = [
    "churn_best.joblib",
    "preprocessor_cls.joblib",
    "kmeans_rfm.joblib",
    "autoencoder_scaler.joblib",
]

OPTIONAL_MODEL_FILES = [
    "delivery_best.joblib",
    "lstm_demand.keras",
    "rnn_demand.keras",
    "gnn_native_recommender.weights.h5",
    "transformer_reviews.keras",
]


def _load_joblib_model(name: str) -> Any:
    if name in MODEL_CACHE:
        return MODEL_CACHE[name]
    model_path = MODELS_DIR / name
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    model = joblib.load(model_path)
    MODEL_CACHE[name] = model
    return model


def _warmup_models() -> None:
    MODEL_LOAD_ERRORS.clear()
    for model_name in CORE_MODEL_FILES + OPTIONAL_MODEL_FILES:
        model_path = MODELS_DIR / model_name
        if not model_path.exists():
            MODEL_LOAD_ERRORS[model_name] = "missing file"
            continue
        if model_name.endswith(".joblib"):
            try:
                _load_joblib_model(model_name)
            except Exception as exc:  # pragma: no cover - defensive branch
                MODEL_LOAD_ERRORS[model_name] = str(exc)
                logger.exception("Failed to load %s", model_name)
        else:
            # Keep heavy deep learning artifacts as discovered metadata by default.
            MODEL_CACHE[model_name] = {"path": str(model_path), "loaded": False}


def _get_required_model(name: str) -> Any:
    try:
        return _load_joblib_model(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cannot load model {name}: {exc}") from exc


def _safe_probability_from_model(model: Any, features: Any) -> float:
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(features)[0, 1])
    prediction = int(model.predict(features)[0])
    return float(prediction)


def _forecast_with_trend(values: List[float], horizon: int) -> List[float]:
    history = np.array(values, dtype=float)
    base = float(history[-7:].mean())
    trend = float((history[-1] - history[0]) / max(1, len(history) - 1))
    forecast: List[float] = []
    for day in range(1, horizon + 1):
        pred = max(0.0, base + trend * day * 0.5)
        forecast.append(round(pred, 3))
    return forecast


def _recommend_by_rules(payload: RecommendationRequest) -> RecommendationResponse:
    segment_catalog = {
        0: ["budget_home", "daily_essentials", "discount_bundle"],
        1: ["beauty_care", "fashion_accessories", "gift_set"],
        2: ["electronics", "gaming_accessories", "smart_home"],
        3: ["premium_audio", "high_end_devices", "extended_warranty"],
    }
    default_catalog = [
        "top_seller_bundle",
        "cross_sell_accessory_pack",
        "new_arrivals",
        "premium_membership_offer",
        "seasonal_collection",
    ]

    pool = list(default_catalog)
    if payload.segment is not None and payload.segment in segment_catalog:
        pool = segment_catalog[payload.segment] + default_catalog
    if payload.recent_categories:
        for category in payload.recent_categories[:3]:
            pool.insert(0, f"{category}_upsell")

    if payload.churn_risk is not None and payload.churn_risk >= 0.7:
        pool.insert(0, "retention_coupon_15")
        pool.insert(1, "loyalty_booster_bundle")

    deduped = list(dict.fromkeys(pool))
    selected = deduped[: payload.top_k]
    return RecommendationResponse(
        recommendations=selected,
        rationale="rule_based_personalization",
        model="gnn_native_recommender_fallback",
    )


def _compute_anomaly_score(features: List[float]) -> float:
    scaler = MODEL_CACHE.get("autoencoder_scaler.joblib")
    x = np.array(features, dtype=float)
    if scaler is None:
        centered = x - x.mean()
        denom = float(np.std(centered) + 1e-6)
        return float(np.mean(np.abs(centered / denom)))

    expected = getattr(scaler, "n_features_in_", None)
    if expected is not None and expected != len(features):
        raise HTTPException(
            status_code=422,
            detail=f"Expected {expected} features for anomaly scoring, got {len(features)}.",
        )

    x2 = np.array([features], dtype=float)
    transformed = scaler.transform(x2)
    score = float(np.mean(np.abs(transformed)))
    return score


@app.on_event("startup")
def startup_event() -> None:
    _warmup_models()
    logger.info("RetailSenseAPI started. Loaded models: %s", list(MODEL_CACHE.keys()))


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    expected = CORE_MODEL_FILES + OPTIONAL_MODEL_FILES
    loaded = [name for name in expected if name in MODEL_CACHE and name not in MODEL_LOAD_ERRORS]
    missing = [name for name in expected if name not in loaded]
    return HealthResponse(
        status="ok",
        api_version=API_VERSION,
        models_loaded=loaded,
        models_missing=missing,
    )


@app.post("/predict/churn", response_model=ChurnResponse, tags=["inference"])
def predict_churn(payload: ChurnRequest) -> ChurnResponse:
    model = _get_required_model("churn_best.joblib")
    preprocessor = _get_required_model("preprocessor_cls.joblib")

    try:
        row = pd.DataFrame([payload.model_dump()])
        transformed = preprocessor.transform(row)
        probability = _safe_probability_from_model(model, transformed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Churn inference failed: {exc}") from exc

    prediction = int(probability >= 0.5)
    return ChurnResponse(prediction=prediction, risk_probability=probability, model="churn_best.joblib")


@app.post("/predict/segmentation", response_model=SegmentationResponse, tags=["inference"])
def predict_segmentation(payload: SegmentationRequest) -> SegmentationResponse:
    model = _get_required_model("kmeans_rfm.joblib")
    features = np.array([[payload.recency, payload.frequency, payload.monetary]], dtype=float)
    try:
        cluster = int(model.predict(features)[0])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Segmentation inference failed: {exc}") from exc
    return SegmentationResponse(cluster=cluster, model="kmeans_rfm.joblib")


@app.post("/predict/demand", response_model=DemandForecastResponse, tags=["inference"])
def predict_demand(payload: DemandForecastRequest) -> DemandForecastResponse:
    sanitized = [max(0.0, float(value)) for value in payload.recent_daily_orders]
    forecast = _forecast_with_trend(sanitized, payload.horizon_days)
    return DemandForecastResponse(
        horizon_days=payload.horizon_days,
        forecast=forecast,
        model="moving_average_trend_v1",
    )


@app.post("/predict/recommendations", response_model=RecommendationResponse, tags=["inference"])
def predict_recommendations(payload: RecommendationRequest) -> RecommendationResponse:
    return _recommend_by_rules(payload)


@app.post("/predict/anomaly", response_model=AnomalyResponse, tags=["inference"])
def predict_anomaly(payload: AnomalyRequest) -> AnomalyResponse:
    score = _compute_anomaly_score(payload.features)
    return AnomalyResponse(
        anomaly_score=round(score, 4),
        is_anomaly=bool(score >= ANOMALY_THRESHOLD),
        threshold=ANOMALY_THRESHOLD,
        model="autoencoder_scaler.joblib",
    )


@app.post("/predict/sentiment", response_model=SentimentResponse, tags=["inference"])
def predict_sentiment(payload: SentimentRequest) -> SentimentResponse:
    text = payload.text.lower()
    positive_words = ["excellent", "good", "great", "love", "satisfied", "happy", "fast", "thanks"]
    negative_words = ["bad", "terrible", "poor", "late", "angry", "disappointed", "issue", "problem"]

    pos_count = sum(1 for word in positive_words if word in text)
    neg_count = sum(1 for word in negative_words if word in text)

    if pos_count > neg_count:
        return SentimentResponse(
            label="positive",
            confidence=min(0.99, 0.6 + 0.1 * pos_count),
            model="transformer_reviews_fallback",
        )
    if neg_count > pos_count:
        return SentimentResponse(
            label="negative",
            confidence=min(0.99, 0.6 + 0.1 * neg_count),
            model="transformer_reviews_fallback",
        )
    return SentimentResponse(label="neutral", confidence=0.6, model="transformer_reviews_fallback")


@app.get("/metadata/models", tags=["system"])
def model_metadata() -> Dict[str, Any]:
    return {
        "models_dir": str(MODELS_DIR),
        "loaded": sorted(MODEL_CACHE.keys()),
        "errors": MODEL_LOAD_ERRORS,
    }
