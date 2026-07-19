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


def _resolve_models_dir() -> Path:
    """Resolve models directory with safe fallbacks for cloud runtimes."""
    configured = os.getenv("RETAILSENSE_MODELS_DIR")
    candidates: List[Path] = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend([ROOT / "models", Path.cwd() / "models"])

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            if configured and str(candidate) != configured:
                logging.getLogger("retailsense.api").warning(
                    "Configured RETAILSENSE_MODELS_DIR=%s not found, using fallback %s",
                    configured,
                    candidate,
                )
            return candidate

    # Last-resort fallback keeps previous behavior if nothing exists yet.
    return Path(configured) if configured else ROOT / "models"


def _resolve_model_registry_path(models_dir: Path) -> Path:
    """Resolve registry path with fallback to models_dir/model_registry.json."""
    configured = os.getenv("RETAILSENSE_MODEL_REGISTRY_PATH")
    fallback = models_dir / "model_registry.json"

    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return configured_path
        if fallback.exists():
            logging.getLogger("retailsense.api").warning(
                "Configured RETAILSENSE_MODEL_REGISTRY_PATH=%s not found, using fallback %s",
                configured,
                fallback,
            )
            return fallback
        return configured_path

    return fallback


MODELS_DIR = _resolve_models_dir()
ANOMALY_THRESHOLD = float(os.getenv("RETAILSENSE_ANOMALY_THRESHOLD", "2.5"))
ANOMALY_THRESHOLD_SAMPLE_MAX = int(os.getenv("RETAILSENSE_ANOMALY_THRESHOLD_SAMPLE_MAX", "3000"))
REQUEST_LOG_ENABLED = os.getenv("RETAILSENSE_REQUEST_LOG_ENABLED", "true").lower() == "true"
LOG_LEVEL = os.getenv("RETAILSENSE_LOG_LEVEL", "INFO").upper()
MODEL_REGISTRY_PATH = _resolve_model_registry_path(MODELS_DIR)

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
    churn_probability: float
    risk_level: str
    message: str


class SegmentationRequest(BaseModel):
    recency: float = Field(..., ge=0)
    frequency: float = Field(..., ge=1)
    monetary: float = Field(..., ge=0)


class SegmentationResponse(BaseModel):
    cluster_id: int
    segment: str
    description: str


class DemandForecastRequest(BaseModel):
    recent_daily_orders: List[float] = Field(..., min_length=7, max_length=120)
    horizon_days: int = Field(7, ge=1, le=30)


class DemandForecastResponse(BaseModel):
    horizon_days: int
    forecast: List[float]
    model: str


class RecommendationRequest(BaseModel):
    customer_id: Optional[str] = None
    segment: Optional[int] = Field(default=None, ge=-1, le=15)
    churn_risk: Optional[float] = Field(default=None, ge=0, le=1)
    recent_categories: List[str] = Field(default_factory=list)
    top_k: int = Field(5, ge=1, le=10)


class RecommendationResponse(BaseModel):
    recommendations: List[str]
    rationale: str
    model: str


class AnomalyRequest(BaseModel):
    total_price: Optional[float] = Field(default=None, ge=0)
    total_freight: Optional[float] = Field(default=None, ge=0)
    total_weight: Optional[float] = Field(default=None, ge=0)
    n_items: Optional[float] = Field(default=None, ge=0)
    max_installments: Optional[float] = Field(default=None, ge=0)
    payment_value: Optional[float] = Field(default=None, ge=0)
    delivery_days: Optional[float] = Field(default=None)
    delay_days: Optional[float] = Field(default=None)
    features: Optional[List[float]] = Field(default=None, min_length=8, max_length=8)


class AnomalyResponse(BaseModel):
    anomaly_score: float
    is_anomaly: bool
    risk_level: str
    message: str


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
    "dbscan_rfm.joblib",
    "autoencoder_scaler_fraud.joblib",
    "autoencoder_fraud_detection.keras",
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
RFM_FEATURE_COLUMNS = ["recency", "frequency", "monetary"]
ANOMALY_FEATURE_COLUMNS = [
    "total_price",
    "total_freight",
    "total_weight",
    "n_items",
    "max_installments",
    "payment_value",
    "delivery_days",
    "delay_days",
]


class _IdentityScaler:
    """Fallback scaler used when training-time data snapshots are unavailable."""

    n_features_in_ = len(RFM_FEATURE_COLUMNS)

    def transform(self, x):
        return np.asarray(x, dtype=float)


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
    tokenizer = Tokenizer(num_words=SENTIMENT_VOCAB_SIZE, oov_token="<OOV>")
    if reviews_path.exists():
        reviews = pd.read_csv(reviews_path)
        reviews = reviews.dropna(subset=["review_comment_message"]).copy()
        reviews = reviews[reviews["review_score"].isin([1, 2, 4, 5])].copy()
        reviews["review_comment_message"] = reviews["review_comment_message"].astype(str)
        reviews = reviews.sample(n=min(8000, len(reviews)), random_state=SEED).reset_index(drop=True)
        tokenizer.fit_on_texts(reviews["review_comment_message"].tolist())
    else:
        # Cloud fallback: keep endpoint available even if raw reviews file is not packaged.
        logger.warning("Tokenizer source file not found at %s, using fallback vocabulary", reviews_path)
        fallback_corpus = [
            "excellent service fast delivery",
            "very good product and quality",
            "bad quality late delivery",
            "not satisfied with purchase",
            "great value and perfect condition",
            "terrible experience and refund requested",
        ]
        tokenizer.fit_on_texts(fallback_corpus)

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


def _load_rfm_preprocessor() -> StandardScaler:
    cache_key = "dbscan_rfm.joblib:scaler"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    rfm_path = ROOT / "data" / "processed" / "rfm_standardized.csv"
    if not rfm_path.exists():
        logger.warning(
            "RFM preprocessing source file not found at %s, using identity scaler fallback.",
            rfm_path,
        )
        scaler = _IdentityScaler()
        MODEL_CACHE[cache_key] = scaler
        return scaler

    rfm_df = pd.read_csv(rfm_path)
    missing = [col for col in RFM_FEATURE_COLUMNS if col not in rfm_df.columns]
    if missing:
        raise ValueError(f"rfm_standardized.csv is missing required columns: {missing}")

    scaler = StandardScaler()
    scaler.fit(rfm_df[RFM_FEATURE_COLUMNS].astype(float).to_numpy())
    MODEL_CACHE[cache_key] = scaler
    return scaler


def _load_rfm_segment_stats() -> Dict[int, Dict[str, float]]:
    cache_key = "dbscan_rfm.joblib:segment_stats"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    segments_path = ROOT / "data" / "processed" / "rfm_segments.csv"
    if not segments_path.exists():
        MODEL_CACHE[cache_key] = {}
        return {}

    seg_df = pd.read_csv(segments_path)
    required = ["dbscan_cluster", "recency", "frequency", "monetary"]
    if any(col not in seg_df.columns for col in required):
        MODEL_CACHE[cache_key] = {}
        return {}

    grouped = (
        seg_df.groupby("dbscan_cluster", dropna=False)
        .agg(
            recency=("recency", "mean"),
            frequency=("frequency", "mean"),
            monetary=("monetary", "mean"),
            nombre_clients=("dbscan_cluster", "count"),
        )
        .reset_index()
    )
    stats: Dict[int, Dict[str, float]] = {}
    for row in grouped.to_dict("records"):
        cluster_id = int(row["dbscan_cluster"])
        stats[cluster_id] = {
            "recency": float(row["recency"]),
            "frequency": float(row["frequency"]),
            "monetary": float(row["monetary"]),
            "nombre_clients": float(row["nombre_clients"]),
        }

    MODEL_CACHE[cache_key] = stats
    return stats


def _transform_rfm_for_dbscan(payload: SegmentationRequest) -> np.ndarray:
    scaler = _load_rfm_preprocessor()
    transformed = np.array(
        [[payload.recency, np.log1p(payload.frequency), np.log1p(payload.monetary)]],
        dtype=float,
    )
    transformed_scaled = scaler.transform(transformed)
    logger.info(
        "segmentation.transform raw=%s log1p_and_scaled=%s",
        {
            "recency": float(payload.recency),
            "frequency": float(payload.frequency),
            "monetary": float(payload.monetary),
        },
        transformed_scaled[0].tolist(),
    )
    return transformed_scaled


def _predict_dbscan_cluster(model: Any, transformed_features: np.ndarray) -> int:
    core_points = getattr(model, "components_", None)
    core_indices = getattr(model, "core_sample_indices_", None)
    labels = getattr(model, "labels_", None)
    eps = float(getattr(model, "eps", 0.5))

    if core_points is None or core_indices is None or labels is None:
        raise ValueError("DBSCAN model does not expose components_, core_sample_indices_ and labels_.")

    core_labels = labels[core_indices]
    distances = np.linalg.norm(core_points - transformed_features[0], axis=1)
    nearest_idx = int(np.argmin(distances))
    nearest_distance = float(distances[nearest_idx])
    if nearest_distance > eps:
        logger.info(
            "segmentation.dbscan nearest_distance=%.6f eps=%.6f cluster=-1",
            nearest_distance,
            eps,
        )
        return -1
    cluster_id = int(core_labels[nearest_idx])
    logger.info(
        "segmentation.dbscan nearest_distance=%.6f eps=%.6f cluster=%s",
        nearest_distance,
        eps,
        cluster_id,
    )
    return cluster_id


def _predict_cluster_from_segment_centroids(transformed_features: np.ndarray) -> int:
    stats = _load_rfm_segment_stats()
    usable = {cluster_id: row for cluster_id, row in stats.items() if cluster_id != -1}
    if not usable:
        raise HTTPException(
            status_code=503,
            detail=(
                "Segmentation DBSCAN unavailable: missing model file and "
                "no usable cluster centroids in rfm_segments.csv."
            ),
        )

    centroid_vectors: Dict[int, np.ndarray] = {}
    for cluster_id, row in usable.items():
        pseudo_payload = SegmentationRequest(
            recency=float(row["recency"]),
            frequency=max(1.0, float(row["frequency"])),
            monetary=max(0.0, float(row["monetary"])),
        )
        centroid_vectors[cluster_id] = _transform_rfm_for_dbscan(pseudo_payload)[0]

    sample = transformed_features[0]
    best_cluster = min(
        centroid_vectors.keys(),
        key=lambda cluster_id: float(np.linalg.norm(centroid_vectors[cluster_id] - sample)),
    )
    return int(best_cluster)


def _describe_segment(cluster_id: int, payload: Optional[SegmentationRequest] = None) -> Dict[str, str]:
    stats = _load_rfm_segment_stats()
    cluster_stats = stats.get(cluster_id)
    logger.info(
        "segmentation.cluster_stats cluster_id=%s stats=%s",
        cluster_id,
        cluster_stats,
    )

    def _finalize(segment: str, description: str) -> Dict[str, str]:
        logger.info(
            "segmentation.mapping cluster_id=%s segment=%s description=%s",
            cluster_id,
            segment,
            description,
        )
        return {
            "segment": segment,
            "description": description,
        }

    if cluster_id == -1:
        if payload is not None:
            if payload.recency <= 60 and payload.frequency >= 4 and payload.monetary >= 800:
                return _finalize(
                    "Client VIP atypique",
                    "Client a forte valeur avec comportement atypique detecte par DBSCAN.",
                )
            if payload.recency >= 220 and payload.frequency <= 2:
                return _finalize(
                    "Client inactif",
                    "Client peu recent avec faible frequence d'achat.",
                )
        return _finalize(
            "Client a surveiller",
            "Comportement atypique detecte par DBSCAN (bruit).",
        )

    if cluster_id not in stats:
        return _finalize(
            "Client actif",
            "Profil detecte sans categorie metier specifique.",
        )

    ref = {k: v for k, v in stats.items() if k != -1}
    if not ref:
        return _finalize(
            "Client actif",
            "Profil client detecte sur la base RFM.",
        )

    row = stats[cluster_id]
    recency = float(row["recency"])
    frequency = float(row["frequency"])
    monetary = float(row["monetary"])

    if recency <= 45 and frequency >= 4 and monetary >= 600:
        return _finalize(
            "Client VIP",
            "Achats recents, frequence elevee et forte valeur d'achat.",
        )
    if recency <= 90 and frequency >= 2 and monetary >= 250:
        return _finalize(
            "Client fidele",
            "Client regulier avec une activite recente.",
        )
    if recency >= 220 and frequency <= 1.5:
        return _finalize(
            "Client inactif",
            "Peu d'achats recents, risque de desengagement.",
        )
    if frequency <= 2 or monetary < 200:
        return _finalize(
            "Client occasionnel",
            "Activite faible avec achats ponctuels.",
        )

    return _finalize(
        "Client actif",
        "Profil intermediaire avec comportement d'achat stable.",
    )


def _load_anomaly_model() -> Any:
    cache_key = "autoencoder_fraud_detection.keras:model"
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    model_path = MODELS_DIR / "autoencoder_fraud_detection.keras"
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = keras.models.load_model(model_path, compile=False)
    MODEL_CACHE[cache_key] = model
    MODEL_CACHE["autoencoder_fraud_detection.keras"] = {"path": str(model_path), "loaded": True}
    return model


def _load_anomaly_scaler() -> StandardScaler:
    scaler_filenames = [
        "autoencoder_scaler_fraud.joblib",
        "autoencoder_scaler_fraude.joblib",
        "autoencoder_scaler.joblib",
    ]

    scaler: Optional[Any] = None
    last_error: Optional[Exception] = None
    for scaler_name in scaler_filenames:
        try:
            scaler = _load_joblib_model(scaler_name)
            break
        except FileNotFoundError as exc:
            last_error = exc
            continue
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Cannot load model {scaler_name}: {exc}") from exc

    if scaler is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Anomaly scaler model file not found. "
                f"Tried: {', '.join(scaler_filenames)}"
            ),
        ) from last_error

    expected = list(getattr(scaler, "feature_names_in_", []))
    if expected and expected != ANOMALY_FEATURE_COLUMNS:
        logger.warning("Unexpected anomaly feature order in scaler: %s", expected)
    return scaler


def _build_anomaly_vector(payload: AnomalyRequest) -> List[float]:
    if payload.features is not None:
        if len(payload.features) != len(ANOMALY_FEATURE_COLUMNS):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Invalid anomaly feature vector length: "
                    f"expected {len(ANOMALY_FEATURE_COLUMNS)} values ordered as "
                    f"{ANOMALY_FEATURE_COLUMNS}"
                ),
            )
        return [float(value) for value in payload.features]

    values: Dict[str, Optional[float]] = {
        "total_price": payload.total_price,
        "total_freight": payload.total_freight,
        "total_weight": payload.total_weight,
        "n_items": payload.n_items,
        "max_installments": payload.max_installments,
        "payment_value": payload.payment_value,
        "delivery_days": payload.delivery_days,
        "delay_days": payload.delay_days,
    }
    missing = [key for key, value in values.items() if value is None]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing anomaly features: {', '.join(missing)}",
        )
    return [float(values[col]) for col in ANOMALY_FEATURE_COLUMNS]


def _compute_anomaly_threshold(model: Any, scaler: StandardScaler) -> float:
    cache_key = "autoencoder_fraud_detection.keras:threshold"
    if cache_key in MODEL_CACHE:
        return float(MODEL_CACHE[cache_key])

    data_path = ROOT / "data" / "processed" / "orders_features.csv"
    if not data_path.exists():
        logger.warning(
            "Anomaly threshold source file not found at %s, using configured fallback threshold=%s",
            data_path,
            ANOMALY_THRESHOLD,
        )
        MODEL_CACHE[cache_key] = float(ANOMALY_THRESHOLD)
        return float(ANOMALY_THRESHOLD)

    df = pd.read_csv(data_path)
    missing = [col for col in ANOMALY_FEATURE_COLUMNS if col not in df.columns]
    if missing:
        logger.warning(
            "orders_features.csv missing anomaly columns %s, using configured fallback threshold=%s",
            missing,
            ANOMALY_THRESHOLD,
        )
        MODEL_CACHE[cache_key] = float(ANOMALY_THRESHOLD)
        return float(ANOMALY_THRESHOLD)

    ref = df[ANOMALY_FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").dropna()
    if ref.empty:
        logger.warning(
            "orders_features.csv has no usable rows for anomaly threshold, using configured fallback threshold=%s",
            ANOMALY_THRESHOLD,
        )
        MODEL_CACHE[cache_key] = float(ANOMALY_THRESHOLD)
        return float(ANOMALY_THRESHOLD)

    if len(ref) > ANOMALY_THRESHOLD_SAMPLE_MAX:
        ref = ref.sample(n=ANOMALY_THRESHOLD_SAMPLE_MAX, random_state=SEED)

    transformed = scaler.transform(ref)
    reconstructed = model.predict(transformed, verbose=0, batch_size=512)
    errors = np.mean(np.square(transformed - reconstructed), axis=1)
    threshold = float(np.percentile(errors, 95))
    MODEL_CACHE[cache_key] = threshold
    return threshold


def _score_anomaly(values: List[float]) -> Dict[str, float | bool]:
    scaler = _load_anomaly_scaler()
    model = _load_anomaly_model()

    expected = getattr(scaler, "n_features_in_", None)
    if expected is not None and expected != len(values):
        raise HTTPException(
            status_code=422,
            detail=f"Expected {expected} features for anomaly scoring, got {len(values)}.",
        )

    vector_df = pd.DataFrame([values], columns=ANOMALY_FEATURE_COLUMNS)
    transformed = scaler.transform(vector_df)
    reconstructed = model.predict(transformed, verbose=0, batch_size=1)
    reconstruction_error = float(np.mean(np.square(transformed - reconstructed), axis=1)[0])
    threshold = _compute_anomaly_threshold(model, scaler)
    ratio = reconstruction_error / max(threshold, 1e-9)

    return {
        "error": reconstruction_error,
        "threshold": threshold,
        "score": float(min(1.5, max(0.0, ratio))),
        "is_anomaly": bool(reconstruction_error >= threshold),
    }


def _recommendation_priority_terms(payload: RecommendationRequest) -> Dict[str, float]:
    """Build lightweight business priors so recommendations react to client profile."""
    priorities: Dict[str, float] = {}

    segment = payload.segment
    if segment == 0:
        priorities.update({"housewares": 0.20, "bed_bath_table": 0.20, "toys": 0.15})
    elif segment == 1:
        priorities.update({"computers": 0.20, "watches": 0.20, "telephony": 0.15})
    elif segment == 2:
        priorities.update({"furniture": 0.20, "auto": 0.20, "computers": 0.15})
    elif segment == 3:
        priorities.update({"health": 0.25, "housewares": 0.20, "sports": 0.10})
    elif segment == 4:
        priorities.update({"sports": 0.15, "toys": 0.15, "housewares": 0.10})

    if payload.churn_risk is not None:
        if payload.churn_risk >= 0.75:
            priorities["housewares"] = max(priorities.get("housewares", 0.0), 0.30)
            priorities["health"] = max(priorities.get("health", 0.0), 0.30)
            priorities["toys"] = max(priorities.get("toys", 0.0), 0.20)
        elif payload.churn_risk >= 0.50:
            priorities["sports"] = max(priorities.get("sports", 0.0), 0.20)
            priorities["housewares"] = max(priorities.get("housewares", 0.0), 0.20)
        elif payload.churn_risk < 0.20:
            priorities["computers"] = max(priorities.get("computers", 0.0), 0.20)
            priorities["watches"] = max(priorities.get("watches", 0.0), 0.20)

    return priorities


def _profile_priority_score(category: str, priorities: Dict[str, float]) -> float:
    name = category.lower().strip()
    score = 0.0
    for term, weight in priorities.items():
        if term in name:
            score += weight
    return score


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
    priorities = _recommendation_priority_terms(payload)

    ranked_candidates = sorted(
        candidates,
        key=lambda cat: _profile_priority_score(cat, priorities),
        reverse=True,
    )
    selected = [cat for cat in ranked_candidates if cat not in excluded][: payload.top_k]

    # Add a deterministic variation so close profiles don't always see the same ordering.
    if selected:
        shift_base = int((payload.segment or 0) + round((payload.churn_risk or 0.0) * 10))
        shift = shift_base % len(selected)
        selected = selected[shift:] + selected[:shift]

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
    query_source = "global"
    if payload.customer_id:
        customer_key = str(payload.customer_id)
        if customer_key in cust_map:
            query_embedding = embeddings[cust_map[customer_key]]
            query_source = "customer"

    if query_embedding is None and payload.recent_categories:
        known_recent = [c for c in payload.recent_categories if c in prod_map]
        if known_recent:
            query_embedding = embeddings[[prod_map[c] for c in known_recent]].mean(axis=0)
            query_source = "recent_categories"

    if query_embedding is None:
        query_embedding = product_embeddings.mean(axis=0)

    scores = np.dot(product_embeddings, query_embedding)
    priorities = _recommendation_priority_terms(payload)

    if priorities:
        profile_boost = np.array(
            [_profile_priority_score(product, priorities) for product in products],
            dtype=np.float32,
        )
        # Stronger profile weighting when query context is weak.
        profile_weight = 2.5 if query_source == "global" else 1.2
        scores = scores + (profile_boost * profile_weight)

    # Deterministic variation by profile to avoid identical outputs for nearby clients.
    if payload.segment is not None or payload.churn_risk is not None:
        shift = int((payload.segment or 0) + round((payload.churn_risk or 0.0) * 10))
        if len(scores) > 0 and shift > 0:
            scores = np.roll(scores, shift % len(scores))

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


@app.on_event("startup")
def startup_event() -> None:
    _load_model_registry()
    _warmup_models()
    # Warm anomaly dependencies upfront to reduce first-request latency in cloud gateways.
    try:
        scaler = _load_anomaly_scaler()
        model = _load_anomaly_model()
        _compute_anomaly_threshold(model, scaler)
    except Exception as exc:  # pragma: no cover - best effort warmup
        logger.warning("Anomaly warmup skipped: %s", exc)
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


@app.get("/health/models-files", tags=["system"])
def health_models_files() -> Dict[str, Any]:
    tracked = sorted(
        set(
            CORE_MODEL_FILES
            + [
                "autoencoder_scaler_fraude.joblib",
                "autoencoder_scaler.joblib",
            ]
        )
    )

    files: Dict[str, Dict[str, Any]] = {}
    for name in tracked:
        path = MODELS_DIR / name
        exists = path.exists()
        files[name] = {
            "exists": exists,
            "size_bytes": int(path.stat().st_size) if exists else None,
            "path": str(path),
        }

    sample_dir_entries: List[str] = []
    if MODELS_DIR.exists() and MODELS_DIR.is_dir():
        sample_dir_entries = sorted([entry.name for entry in MODELS_DIR.iterdir()])[:50]

    return {
        "status": "ok",
        "models_dir": str(MODELS_DIR),
        "models_dir_exists": MODELS_DIR.exists(),
        "models_dir_is_dir": MODELS_DIR.is_dir(),
        "tracked_files": files,
        "models_dir_sample_entries": sample_dir_entries,
        "load_errors": MODEL_LOAD_ERRORS,
    }


@app.get("/health/data-files", tags=["system"])
def health_data_files() -> Dict[str, Any]:
    tracked_paths = [
        ROOT / "data" / "processed" / "orders_features.csv",
        ROOT / "data" / "processed" / "rfm_standardized.csv",
        ROOT / "data" / "processed" / "rfm_segments.csv",
        ROOT / "data" / "raw" / "olist_order_reviews_dataset.csv",
    ]

    tracked: Dict[str, Dict[str, Any]] = {}
    for path in tracked_paths:
        key = str(path.relative_to(ROOT))
        tracked[key] = {
            "exists": path.exists(),
            "size_bytes": int(path.stat().st_size) if path.exists() else None,
            "path": str(path),
        }

    return {
        "status": "ok",
        "project_root": str(ROOT),
        "tracked_files": tracked,
    }


@app.post("/predict/churn", response_model=ChurnResponse, tags=["inference"])
def predict_churn(payload: ChurnRequest) -> ChurnResponse:
    model = _get_required_model("churn_best.joblib")
    preprocessor = _get_required_model("preprocessor_cls.joblib")

    logger.info("churn.input %s", payload.model_dump())

    try:
        row = pd.DataFrame([payload.model_dump()])
        transformed = preprocessor.transform(row)
        probability = _safe_probability_from_model(model, transformed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Churn inference failed: {exc}") from exc
    if probability >= 0.70:
        risk_level = "Eleve"
        message = "Client inactif depuis plusieurs mois ou engagement en baisse."
    elif probability >= 0.40:
        risk_level = "Moyen"
        message = "Diminution d'activite detectee, un suivi commercial est recommande."
    else:
        risk_level = "Faible"
        message = "Activite client globalement stable."

    logger.info(
        "churn.output probability_raw=%.6f probability_returned=%.4f risk_level=%s",
        probability,
        round(probability, 4),
        risk_level,
    )
    return ChurnResponse(
        churn_probability=round(probability, 4),
        risk_level=risk_level,
        message=message,
    )


@app.post("/predict/segmentation", response_model=SegmentationResponse, tags=["inference"])
def predict_segmentation(payload: SegmentationRequest) -> SegmentationResponse:
    transformed_features = _transform_rfm_for_dbscan(payload)
    logger.info(
        "segmentation.input recency=%s frequency=%s monetary=%s",
        payload.recency,
        payload.frequency,
        payload.monetary,
    )
    try:
        try:
            model = _get_required_model("dbscan_rfm.joblib")
            cluster = _predict_dbscan_cluster(model, transformed_features)
        except HTTPException as exc:
            if exc.status_code != 503:
                raise
            logger.warning("DBSCAN model unavailable, using centroid fallback: %s", exc.detail)
            cluster = _predict_cluster_from_segment_centroids(transformed_features)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Segmentation inference failed: {exc}") from exc
    profile = _describe_segment(cluster, payload)
    logger.info(
        "segmentation.output cluster_id=%s segment=%s description=%s",
        cluster,
        profile["segment"],
        profile["description"],
    )
    return SegmentationResponse(
        cluster_id=cluster,
        segment=profile["segment"],
        description=profile["description"],
    )


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


def _predict_recommendations_impl(payload: RecommendationRequest) -> RecommendationResponse:
    try:
        logger.info("recommendations.input %s", payload.model_dump())
        response = _recommend_by_gnn(payload)
        logger.info(
            "recommendations.output count=%s rationale=%s items=%s",
            len(response.recommendations),
            response.rationale,
            response.recommendations,
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recommendations inference failed: {exc}") from exc


@app.post("/recommend/products", response_model=RecommendationResponse, tags=["inference"])
def recommend_products(payload: RecommendationRequest) -> RecommendationResponse:
    return _predict_recommendations_impl(payload)


@app.post("/predict/recommendations", response_model=RecommendationResponse, tags=["inference"])
def predict_recommendations(payload: RecommendationRequest) -> RecommendationResponse:
    return _predict_recommendations_impl(payload)


@app.post("/predict/anomaly", response_model=AnomalyResponse, tags=["inference"])
def predict_anomaly(payload: AnomalyRequest) -> AnomalyResponse:
    values = _build_anomaly_vector(payload)
    result = _score_anomaly(values)

    score = float(result["score"])
    is_anomaly = bool(result["is_anomaly"])
    if is_anomaly and score >= 1.2:
        risk_level = "Eleve"
        message = "Commande inhabituelle detectee avec un niveau de risque eleve."
    elif is_anomaly:
        risk_level = "Moyen"
        message = "Comportement atypique detecte, verification recommandee."
    else:
        risk_level = "Faible"
        message = "Comportement conforme aux transactions habituelles."

    return AnomalyResponse(
        anomaly_score=round(score, 4),
        is_anomaly=is_anomaly,
        risk_level=risk_level,
        message=message,
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

        if score >= 0.5:
            return SentimentResponse(
                label="positive",
                confidence=round(max(score, 1.0 - score), 4),
                model="transformer_reviews.keras",
            )

        return SentimentResponse(
            label="negative",
            confidence=round(max(score, 1.0 - score), 4),
            model="transformer_reviews.keras",
        )
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
