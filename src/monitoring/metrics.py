# src/monitoring/metrics.py
"""
Prometheus metrics for the GeoSentinel serving API.
Exposes: prediction counts, latency, drift score, model info.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

REGISTRY = CollectorRegistry()

# Prediction counters
PREDICTIONS_TOTAL = Counter(
    "geosentinel_predictions_total",
    "Total number of predictions made",
    ["result"],          # 'normal' or 'anomaly'
    registry=REGISTRY,
)

# Latency histogram
PREDICTION_LATENCY = Histogram(
    "geosentinel_prediction_latency_seconds",
    "Prediction latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# Current drift score (updated when drift check runs)
DRIFT_SCORE = Gauge(
    "geosentinel_drift_score",
    "Current data drift score (0=no drift, 1=full drift)",
    registry=REGISTRY,
)

# Anomaly rate gauge
ANOMALY_RATE = Gauge(
    "geosentinel_anomaly_rate",
    "Rolling anomaly detection rate (last 100 predictions)",
    registry=REGISTRY,
)

# Model version info
MODEL_VERSION = Gauge(
    "geosentinel_model_version",
    "Currently loaded model version",
    registry=REGISTRY,
)
