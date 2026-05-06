# src/serving/app.py
"""
FastAPI serving endpoint for the GeoSentinel anomaly detection model.
Loads the Production model from MLflow Model Registry at startup.

Endpoints:
  GET  /health        — liveness check
  GET  /model/info    — current model version + metadata
  POST /predict       — run anomaly detection on NDVI features
  POST /predict/batch — run on multiple scenes at once
"""

import os
import json
import mlflow
import mlflow.sklearn
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "sqlite:////workspaces/geosentinel-mlops/mlflow/mlflow.db"
)
MODEL_NAME = os.getenv("MODEL_NAME", "geosentinel-anomaly-detector")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Staging")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="GeoSentinel Anomaly Detection API",
    description="Detect vegetation anomalies in Sentinel-2 NDVI data",
    version="0.1.0",
)

# ── Global model state ────────────────────────────────────────────────────────
model = None
model_info = {}


@app.on_event("startup")
def load_model():
    """Load model from MLflow registry at startup."""
    global model, model_info

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()

    print(f"🔍 Loading model: {MODEL_NAME} @ stage={MODEL_STAGE}")

    try:
        model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
        model = mlflow.sklearn.load_model(model_uri)

        # Get version metadata
        versions = client.get_latest_versions(MODEL_NAME, stages=[MODEL_STAGE])
        if versions:
            v = versions[0]
            model_info = {
                "name": MODEL_NAME,
                "version": v.version,
                "stage": v.current_stage,
                "run_id": v.run_id,
                "loaded_at": datetime.utcnow().isoformat(),
            }

        print(f"✅ Model loaded — Version {model_info.get('version')} ({MODEL_STAGE})")

    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        raise RuntimeError(f"Model load failed: {e}")


# ── Request / Response schemas ────────────────────────────────────────────────

class NDVIFeatures(BaseModel):
    """NDVI feature vector for a single Sentinel-2 scene."""
    scene:          Optional[str]  = Field(None, description="Scene identifier")
    ndvi_mean:      float = Field(..., description="Mean NDVI value across the tile")
    ndvi_std:       float = Field(..., description="Standard deviation of NDVI")
    ndvi_min:       float = Field(..., description="Minimum NDVI value")
    ndvi_max:       float = Field(..., description="Maximum NDVI value")
    vegetation_pct: float = Field(..., description="% pixels with NDVI > 0.3")
    water_pct:      float = Field(..., description="% pixels with NDVI < 0.0")
    bare_soil_pct:  float = Field(..., description="% pixels with NDVI 0.0-0.1")

    model_config = {
        "json_schema_extra": {
            "example": {
                "scene": "S2A_32UMA_20240605_0_L2A",
                "ndvi_mean": 0.027,
                "ndvi_std": 0.049,
                "ndvi_min": -0.250,
                "ndvi_max": 0.812,
                "vegetation_pct": 0.62,
                "water_pct": 8.15,
                "bare_soil_pct": 87.25,
            }
        }
    }


class PredictionResponse(BaseModel):
    """Anomaly detection result for a single scene."""
    scene:        Optional[str]
    prediction:   str   = Field(..., description="'anomaly' or 'normal'")
    anomaly_score: float = Field(..., description="Score: negative = more anomalous")
    is_anomaly:   bool
    model_version: str
    model_stage:  str


class BatchRequest(BaseModel):
    scenes: list[NDVIFeatures]


class BatchResponse(BaseModel):
    results: list[PredictionResponse]
    total:   int
    anomaly_count: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness check."""
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/model/info")
def get_model_info():
    """Return current model version and metadata."""
    if not model_info:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return model_info


@app.post("/predict", response_model=PredictionResponse)
def predict(features: NDVIFeatures):
    """Run anomaly detection on a single scene's NDVI features."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    X = np.array([[
        features.ndvi_mean,
        features.ndvi_std,
        features.ndvi_min,
        features.ndvi_max,
        features.vegetation_pct,
        features.water_pct,
        features.bare_soil_pct,
    ]], dtype=np.float32)

    score = float(model.decision_function(X)[0])
    pred  = int(model.predict(X)[0])  # -1 = anomaly, 1 = normal

    return PredictionResponse(
        scene=features.scene,
        prediction="anomaly" if pred == -1 else "normal",
        anomaly_score=round(score, 6),
        is_anomaly=pred == -1,
        model_version=str(model_info.get("version", "unknown")),
        model_stage=MODEL_STAGE,
    )


@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(request: BatchRequest):
    """Run anomaly detection on multiple scenes at once."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.scenes:
        raise HTTPException(status_code=400, detail="No scenes provided")

    X = np.array([[
        f.ndvi_mean, f.ndvi_std, f.ndvi_min, f.ndvi_max,
        f.vegetation_pct, f.water_pct, f.bare_soil_pct,
    ] for f in request.scenes], dtype=np.float32)

    scores = model.decision_function(X)
    preds  = model.predict(X)

    results = [
        PredictionResponse(
            scene=f.scene,
            prediction="anomaly" if p == -1 else "normal",
            anomaly_score=round(float(s), 6),
            is_anomaly=p == -1,
            model_version=str(model_info.get("version", "unknown")),
            model_stage=MODEL_STAGE,
        )
        for f, s, p in zip(request.scenes, scores, preds)
    ]

    return BatchResponse(
        results=results,
        total=len(results),
        anomaly_count=sum(1 for r in results if r.is_anomaly),
    )
