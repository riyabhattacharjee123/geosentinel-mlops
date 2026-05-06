# src/serving/app.py
"""
FastAPI serving endpoint for GeoSentinel anomaly detection.
Exposes Prometheus metrics at /metrics.
"""

import os, json, time
import mlflow, mlflow.sklearn
import numpy as np
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import sys
from pathlib import Path

sys.path.insert(0, "/workspaces/geosentinel-mlops")

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI",
    "sqlite:////workspaces/geosentinel-mlops/mlflow/mlflow.db")
MODEL_NAME  = os.getenv("MODEL_NAME",  "geosentinel-anomaly-detector")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Staging")

app = FastAPI(
    title="GeoSentinel Anomaly Detection API",
    description="Detect vegetation anomalies in Sentinel-2 NDVI data",
    version="0.2.0",
)

model      = None
model_info = {}

# Import metrics registry
try:
    from src.monitoring.metrics import (
        REGISTRY, PREDICTIONS_TOTAL, PREDICTION_LATENCY,
        DRIFT_SCORE, ANOMALY_RATE, MODEL_VERSION
    )
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False


@app.on_event("startup")
def load_model():
    global model, model_info
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()
    print(f"🔍 Loading model: {MODEL_NAME} @ stage={MODEL_STAGE}")
    try:
        model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
        model = mlflow.sklearn.load_model(model_uri)
        versions = client.get_latest_versions(MODEL_NAME, stages=[MODEL_STAGE])
        if versions:
            v = versions[0]
            model_info = {
                "name": MODEL_NAME, "version": v.version,
                "stage": v.current_stage, "run_id": v.run_id,
                "loaded_at": datetime.utcnow().isoformat(),
            }
            if METRICS_ENABLED:
                MODEL_VERSION.set(float(v.version))
        print(f"✅ Model loaded — Version {model_info.get('version')} ({MODEL_STAGE})")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        raise RuntimeError(f"Model load failed: {e}")


class NDVIFeatures(BaseModel):
    scene:          Optional[str]  = None
    ndvi_mean:      float
    ndvi_std:       float
    ndvi_min:       float
    ndvi_max:       float
    vegetation_pct: float
    water_pct:      float
    bare_soil_pct:  float
    model_config = {"protected_namespaces": ()}


class PredictionResponse(BaseModel):
    scene:         Optional[str]
    prediction:    str
    anomaly_score: float
    is_anomaly:    bool
    model_version: str
    model_stage:   str
    model_config = {"protected_namespaces": ()}


class BatchRequest(BaseModel):
    scenes: list[NDVIFeatures]

class BatchResponse(BaseModel):
    results:       list[PredictionResponse]
    total:         int
    anomaly_count: int


def _to_array(f: NDVIFeatures) -> np.ndarray:
    return np.array([[
        f.ndvi_mean, f.ndvi_std, f.ndvi_min, f.ndvi_max,
        f.vegetation_pct, f.water_pct, f.bare_soil_pct,
    ]], dtype=np.float32)


def _make_response(f, score, pred) -> PredictionResponse:
    result = "anomaly" if pred == -1 else "normal"
    if METRICS_ENABLED:
        PREDICTIONS_TOTAL.labels(result=result).inc()
    return PredictionResponse(
        scene=f.scene,
        prediction=result,
        anomaly_score=round(float(score), 6),
        is_anomaly=pred == -1,
        model_version=str(model_info.get("version", "unknown")),
        model_stage=MODEL_STAGE,
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None,
            "timestamp": datetime.utcnow().isoformat()}


@app.get("/model/info")
def get_model_info():
    if not model_info:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return model_info


@app.post("/predict", response_model=PredictionResponse)
def predict(features: NDVIFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    start = time.time()
    X = _to_array(features)
    score = float(model.decision_function(X)[0])
    pred  = int(model.predict(X)[0])
    if METRICS_ENABLED:
        PREDICTION_LATENCY.observe(time.time() - start)
    return _make_response(features, score, pred)


@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(request: BatchRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    X = np.array([[
        f.ndvi_mean, f.ndvi_std, f.ndvi_min, f.ndvi_max,
        f.vegetation_pct, f.water_pct, f.bare_soil_pct,
    ] for f in request.scenes], dtype=np.float32)
    scores = model.decision_function(X)
    preds  = model.predict(X)
    results = [_make_response(f, s, p)
               for f, s, p in zip(request.scenes, scores, preds)]
    return BatchResponse(
        results=results, total=len(results),
        anomaly_count=sum(1 for r in results if r.is_anomaly),
    )


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    if not METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    return Response(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/drift/check")
def check_drift():
    """Run drift detection and return summary."""
    try:
        sys.path.insert(0, "/workspaces/geosentinel-mlops")
        from src.monitoring.drift_detector import run_drift_check
        result = run_drift_check()
        if METRICS_ENABLED:
            DRIFT_SCORE.set(result["drift_score"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
