import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import unicodedata
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from scipy import sparse
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.text import Tokenizer  # type: ignore[reportMissingImports, reportMissingModuleSource]
from tensorflow.keras.preprocessing.sequence import pad_sequences  # type: ignore[reportMissingImports, reportMissingModuleSource]
ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = Path(os.getenv("RETAILSENSE_MODELS_DIR", ROOT / "models"))
ANOMALY_THRESHOLD = float(os.getenv("RETAILSENSE_ANOMALY_THRESHOLD", "2.5"))
REQUEST_LOG_ENABLED = os.getenv("RETAILSENSE_REQUEST_LOG_ENABLED", "true").lower() == "true"
LOG_LEVEL = os.getenv("RETAILSENSE_LOG_LEVEL", "INFO").upper()
MODEL_REGISTRY_PATH = Path(os.getenv("RETAILSENSE_MODEL_REGISTRY_PATH", MODELS_DIR / "model_registry.json"))

API_TITLE = "RetailSenseAI API"
API_VERSION = os.getenv("RETAILSENSE_API_VERSION", "1.1.0")

logger = logging.getLogger("retailsense.api")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="REST API for RetailSenseAI model inference services.",
)


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "service": API_TITLE, "docs": "/docs"}

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
    recency: float = Field(..., ge=0)
    frequency: float = Field(..., ge=1)
    monetary: float = Field(..., ge=0)


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
MODEL_REGISTRY: Dict[str, Any] = {}

CORE_MODEL_FILES = [
    "churn_best.joblib",
    "preprocessor_cls.joblib",
    "kmeans_rfm.joblib",
    "autoencoder_scaler.joblib",
    "delivery_best.joblib",
    "lstm_demand.keras",
    "rnn_demand.keras",
    "gnn_native_recommender.weights.h5",
    "transformer_reviews.keras",
]

SEED = 42
SENTIMENT_MAX_LEN = 80
SENTIMENT_VOCAB_SIZE = 10000
DEMAND_LOOK_BACK = 14


class TransformerBlock(layers.Layer):
    def __init__(self, embed_dim: int, num_heads: int, ff_dim: int, rate: float = 0.1, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.ff_dim = ff_dim
        self.rate = rate
        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim // num_heads)
        self.ffn = keras.Sequential(
            [
                layers.Dense(ff_dim, activation="relu"),
                layers.Dense(embed_dim),
            ]
        )
        self.layernorm1 = layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = layers.Dropout(rate)
        self.dropout2 = layers.Dropout(rate)

    def call(self, inputs, training=None):
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)

    def get_config(self):
        config = super().get_config()
        config.update(
            {
                "embed_dim": self.embed_dim,
                "num_heads": self.num_heads,
                "ff_dim": self.ff_dim,
                "rate": self.rate,
            }
        )
        return config


class NativeGCNLayer(tf.keras.layers.Layer):
    def __init__(self, units: int, activation: str = "relu", **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.activation = tf.keras.activations.get(activation)

    def build(self, input_shape):
        self.w = self.add_weight(
            shape=(input_shape[0][-1], self.units),
            initializer="glorot_uniform",
            trainable=True,
        )
        self.b = self.add_weight(shape=(self.units,), initializer="zeros", trainable=True)

    def call(self, inputs):
        x, a = inputs
        x_w = tf.matmul(x, self.w)
        out = tf.sparse.sparse_dense_matmul(a, x_w)
        return self.activation(out + self.b)


class GNNRecommender(tf.keras.Model):
    def __init__(self, n_hidden: int):
        super().__init__()
        self.gcn1 = NativeGCNLayer(n_hidden, name="gcn1")
        self.gcn2 = NativeGCNLayer(n_hidden, name="gcn2")

    def call(self, inputs):
        x, a = inputs
        x = self.gcn1([x, a])
        x = self.gcn2([x, a])
        return x


def _load_joblib_model(name: str) -> Any:
    if name in MODEL_CACHE:
        return MODEL_CACHE[name]
    model_path = MODELS_DIR / name
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    model = joblib.load(model_path)
    MODEL_CACHE[name] = model
    return model


def _load_model_registry() -> None:
    MODEL_REGISTRY.clear()
    if not MODEL_REGISTRY_PATH.exists():
        logger.warning("Model registry file not found at %s", MODEL_REGISTRY_PATH)
        return
    try:
        raw = MODEL_REGISTRY_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            MODEL_REGISTRY.update(parsed)
        else:
            logger.warning("Model registry has invalid format (expected object)")
    except Exception as exc:  # pragma: no cover - defensive branch
        logger.exception("Failed to load model registry: %s", exc)


def _warmup_models() -> None:
    MODEL_LOAD_ERRORS.clear()
    for model_name in CORE_MODEL_FILES:
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


def _load_transformer_sentiment_model() -> Any:
    cache_key = "transformer_reviews.keras:model"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    model_path = MODELS_DIR / "transformer_reviews.keras"
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = keras.models.load_model(
        model_path,
        custom_objects={"TransformerBlock": TransformerBlock},
        compile=False,
    )
    MODEL_CACHE[cache_key] = model
    MODEL_CACHE["transformer_reviews.keras"] = {"path": str(model_path), "loaded": True}
    return model


def _load_sentiment_tokenizer() -> Any:
    cache_key = "transformer_reviews.keras:tokenizer"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    reviews_path = ROOT / "data" / "raw" / "olist_order_reviews_dataset.csv"
    if not reviews_path.exists():
        raise FileNotFoundError(f"Tokenizer source file not found: {reviews_path}")

    reviews = pd.read_csv(reviews_path)
    reviews = reviews.dropna(subset=["review_comment_message"]).copy()
    reviews = reviews[reviews["review_score"].isin([1, 2, 4, 5])].copy()
    reviews["review_comment_message"] = reviews["review_comment_message"].astype(str)
    reviews = reviews.sample(n=min(8000, len(reviews)), random_state=SEED).reset_index(drop=True)

    tokenizer = Tokenizer(num_words=SENTIMENT_VOCAB_SIZE, oov_token="<OOV>")
    tokenizer.fit_on_texts(reviews["review_comment_message"].tolist())
    MODEL_CACHE[cache_key] = tokenizer
    return tokenizer


def _load_demand_rnn_model() -> Any:
    cache_key = "rnn_demand.keras:model"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    model_path = MODELS_DIR / "rnn_demand.keras"
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = keras.models.load_model(model_path, compile=False)
    MODEL_CACHE[cache_key] = model
    MODEL_CACHE["rnn_demand.keras"] = {"path": str(model_path), "loaded": True}
    return model


def _load_demand_scaler() -> StandardScaler:
    cache_key = "rnn_demand.keras:scaler"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    daily_path = MODELS_DIR / "daily_orders.csv"
    if not daily_path.exists():
        raise FileNotFoundError(f"Demand series source file not found: {daily_path}")

    daily = pd.read_csv(daily_path)
    if "orders_count" not in daily.columns:
        raise ValueError("daily_orders.csv must contain 'orders_count' column")

    values = daily["orders_count"].astype(float).to_numpy().reshape(-1, 1)
    if len(values) <= DEMAND_LOOK_BACK:
        raise ValueError("daily_orders.csv does not contain enough rows for RNN scaling")

    train_size = int(len(values) * 0.8)
    train_values = values[:train_size]
    scaler = StandardScaler()
    scaler.fit(train_values)
    MODEL_CACHE[cache_key] = scaler
    return scaler


def _load_gnn_artifacts() -> Dict[str, Any]:
    cache_key = "gnn_native_recommender:artifacts"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    weights_path = MODELS_DIR / "gnn_native_recommender.weights.h5"
    if not weights_path.exists():
        raise FileNotFoundError(f"Model file not found: {weights_path}")

    orders_path = ROOT / "data" / "processed" / "orders_features.csv"
    if not orders_path.exists():
        raise FileNotFoundError(f"Graph source file not found: {orders_path}")

    try:
        df_gnn = pd.read_csv(orders_path, usecols=["customer_id", "main_category"]).dropna().copy()
        if df_gnn.empty:
            raise ValueError("orders_features.csv does not contain graph data for GNN")

        customers = df_gnn["customer_id"].astype(str).unique().tolist()
        products = df_gnn["main_category"].astype(str).unique().tolist()

        cust_map = {cid: i for i, cid in enumerate(customers)}
        prod_map = {pid: i + len(customers) for i, pid in enumerate(products)}
        n_nodes = len(customers) + len(products)

        edges_from = df_gnn["customer_id"].astype(str).map(cust_map).to_numpy()
        edges_to = df_gnn["main_category"].astype(str).map(prod_map).to_numpy()

        adj = sparse.coo_matrix((np.ones(len(edges_from)), (edges_from, edges_to)), shape=(n_nodes, n_nodes))
        adj = (adj + adj.T + sparse.eye(n_nodes)).tocoo()
        d_inv_sqrt = np.power(np.array(adj.sum(1)), -0.5).flatten()
        d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.0
        d_mat = sparse.diags(d_inv_sqrt)
        adj_norm_sp = d_mat.dot(adj).dot(d_mat).tocoo()

        indices = np.vstack((adj_norm_sp.row, adj_norm_sp.col)).T
        adj_tensor = tf.SparseTensor(indices, adj_norm_sp.data.astype("float32"), adj_norm_sp.shape)
        adj_tensor = tf.sparse.reorder(adj_tensor)

        x_gnn = tf.eye(n_nodes, 32, dtype=tf.float32)
        model_gnn = GNNRecommender(32)
        _ = model_gnn([x_gnn, adj_tensor])
        
        logger.info(f"Loading GNN weights from {weights_path}")
        model_gnn.load_weights(str(weights_path))
        embeddings = model_gnn([x_gnn, adj_tensor]).numpy()

        artifacts = {
            "embeddings": embeddings,
            "customers": customers,
            "products": products,
            "cust_map": cust_map,
            "prod_map": prod_map,
        }
        MODEL_CACHE[cache_key] = artifacts
        MODEL_CACHE["gnn_native_recommender.weights.h5"] = {"path": str(weights_path), "loaded": True}
        logger.info(f"GNN artifacts loaded successfully: {len(customers)} customers, {len(products)} products")
        return artifacts
    except Exception as exc:
        logger.exception(f"Failed to load GNN artifacts: {exc}")
        raise


def _forecast_with_rnn(values: List[float], horizon: int) -> List[float]:
    model = _load_demand_rnn_model()
    scaler = _load_demand_scaler()

    series = np.array([max(0.0, float(v)) for v in values], dtype=float).reshape(-1, 1)
    if series.shape[0] < DEMAND_LOOK_BACK:
        pad_count = DEMAND_LOOK_BACK - series.shape[0]
        series = np.vstack([np.repeat(series[:1], pad_count, axis=0), series])

    scaled = scaler.transform(series).flatten().tolist()
    window = scaled[-DEMAND_LOOK_BACK:]

    forecast: List[float] = []
    for _ in range(horizon):
        x = np.array(window[-DEMAND_LOOK_BACK:], dtype=np.float32).reshape(1, DEMAND_LOOK_BACK, 1)
        pred_scaled = float(model.predict(x, verbose=0).ravel()[0])
        pred_value = float(scaler.inverse_transform(np.array([[pred_scaled]], dtype=np.float32))[0, 0])
        forecast.append(round(max(0.0, pred_value), 3))
        window.append(pred_scaled)
    return forecast


def _recommend_by_rules(payload: RecommendationRequest) -> RecommendationResponse:
    """Fallback recommendation strategy used when GNN artifacts are unavailable."""
    candidates: List[str] = [
        "health_beauty",
        "computers_accessories",
        "watches_gifts",
        "bed_bath_table",
        "sports_leisure",
        "furniture_decor",
        "telephony",
        "housewares",
        "auto",
        "toys",
    ]

    excluded = {str(cat).strip() for cat in payload.recent_categories if str(cat).strip()}
    selected = [cat for cat in candidates if cat not in excluded][: payload.top_k]

    if len(selected) < payload.top_k:
        for cat in candidates:
            if cat in selected:
                continue
            selected.append(cat)
            if len(selected) >= payload.top_k:
                break

    return RecommendationResponse(
        recommendations=selected,
        rationale="rules_fallback_top_categories",
        model="rules_fallback",
    )


def _recommend_by_gnn(payload: RecommendationRequest) -> RecommendationResponse:
    try:
        artifacts = _load_gnn_artifacts()
    except Exception as exc:
        logger.exception(f"GNN loading failed, using fallback: {exc}")
        # Fallback: Return segment-based product recommendations
        return _recommend_by_rules(payload)
    
    embeddings = artifacts["embeddings"]
    products = artifacts["products"]
    cust_map = artifacts["cust_map"]
    prod_map = artifacts["prod_map"]

    product_indices = list(prod_map.values())
    product_embeddings = embeddings[product_indices]

    query_embedding: Optional[np.ndarray] = None
    if payload.customer_id:
        customer_key = str(payload.customer_id)
        if customer_key in cust_map:
            query_embedding = embeddings[cust_map[customer_key]]

    if query_embedding is None and payload.recent_categories:
        known_recent = [c for c in payload.recent_categories if c in prod_map]
        if known_recent:
            query_embedding = embeddings[[prod_map[c] for c in known_recent]].mean(axis=0)

    if query_embedding is None:
        query_embedding = product_embeddings.mean(axis=0)

    scores = np.dot(product_embeddings, query_embedding)
    ranking = np.argsort(scores)[::-1]
    excluded = set(payload.recent_categories)

    selected: List[str] = []
    for idx in ranking:
        category = products[idx]
        if category in excluded:
            continue
        selected.append(category)
        if len(selected) >= payload.top_k:
            break

    if len(selected) < payload.top_k:
        for idx in ranking:
            category = products[idx]
            if category in selected:
                continue
            selected.append(category)
            if len(selected) >= payload.top_k:
                break

    return RecommendationResponse(
        recommendations=selected,
        rationale="gnn_embedding_similarity",
        model="gnn_native_recommender.weights.h5",
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
    _load_model_registry()
    _warmup_models()
    logger.info("RetailSenseAPI started. Loaded models: %s", list(MODEL_CACHE.keys()))


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started = time.perf_counter()
    response = None

    if REQUEST_LOG_ENABLED:
        logger.info(
            "request.started request_id=%s method=%s path=%s client=%s",
            request_id,
            request.method,
            request.url.path,
            getattr(request.client, "host", "unknown"),
        )

    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-ms"] = str(elapsed_ms)
        if REQUEST_LOG_ENABLED:
            logger.info(
                "request.completed request_id=%s method=%s path=%s status=%s latency_ms=%s",
                request_id,
                request.method,
                request.url.path,
                getattr(response, "status_code", "error"),
                elapsed_ms,
            )


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    expected = CORE_MODEL_FILES
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
    try:
        sanitized = [max(0.0, float(value)) for value in payload.recent_daily_orders]
        forecast = _forecast_with_rnn(sanitized, payload.horizon_days)
        return DemandForecastResponse(
            horizon_days=payload.horizon_days,
            forecast=forecast,
            model="rnn_demand.keras",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Demand inference failed: {exc}") from exc


@app.post("/predict/recommendations", response_model=RecommendationResponse, tags=["inference"])
def predict_recommendations(payload: RecommendationRequest) -> RecommendationResponse:
    try:
        return _recommend_by_gnn(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recommendations inference failed: {exc}") from exc


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
    try:
        model = _load_transformer_sentiment_model()
        tokenizer = _load_sentiment_tokenizer()

        normalized = unicodedata.normalize("NFKD", payload.text)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = normalized.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)

        seq = tokenizer.texts_to_sequences([normalized])
        x = pad_sequences(
            seq,
            maxlen=SENTIMENT_MAX_LEN,
            padding="post",
            truncating="post",
        )
        score = float(model.predict(x, verbose=0).ravel()[0])

        if score >= 0.52:
            return SentimentResponse(
                label="positive",
                confidence=round(max(score, 1.0 - score), 4),
                model="transformer_reviews.keras",
            )
        if score <= 0.48:
            return SentimentResponse(
                label="negative",
                confidence=round(max(score, 1.0 - score), 4),
                model="transformer_reviews.keras",
            )

        confidence = round(1.0 - abs(score - 0.5) * 2.0, 4)
        return SentimentResponse(label="neutral", confidence=confidence, model="transformer_reviews.keras")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sentiment inference failed: {exc}") from exc


@app.get("/metadata/models", tags=["system"])
def model_metadata() -> Dict[str, Any]:
    registry_models = MODEL_REGISTRY.get("models", {}) if isinstance(MODEL_REGISTRY, dict) else {}
    now_utc = datetime.now(timezone.utc).isoformat()

    return {
        "timestamp_utc": now_utc,
        "models_dir": str(MODELS_DIR),
        "model_registry_path": str(MODEL_REGISTRY_PATH),
        "loaded": sorted(MODEL_CACHE.keys()),
        "errors": MODEL_LOAD_ERRORS,
        "model_versions": registry_models,
    }
