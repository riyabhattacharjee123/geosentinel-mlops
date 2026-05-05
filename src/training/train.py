# src/training/train.py
"""
Train an Isolation Forest anomaly detection model on NDVI features.
All experiments are tracked with MLflow — parameters, metrics, artifacts.

Isolation Forest is ideal here because:
  - We have no labelled anomalies (unsupervised)
  - Seasonal variation = natural concept drift to monitor
  - Fast to train, interpretable contamination parameter
  - Industry standard for time-series anomaly detection
"""

import json
import mlflow
import mlflow.sklearn
import numpy as np
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.training.features import load_all_features, FEATURE_NAMES

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MLFLOW_DIR = Path(__file__).resolve().parents[2] / "mlflow"
MLFLOW_TRACKING_URI = f"sqlite:///{MLFLOW_DIR}/mlflow.db"
EXPERIMENT_NAME = "geosentinel-ndvi-anomaly"


def train(
    contamination: float = 0.05,
    n_estimators: int = 100,
    max_samples: str = "auto",
    random_state: int = 42,
) -> str:
    """
    Train Isolation Forest and log everything to MLflow.

    Args:
        contamination : expected fraction of anomalies (0.01 to 0.5)
        n_estimators  : number of trees in the forest
        max_samples   : samples per tree ('auto' = min(256, n_samples))
        random_state  : seed for reproducibility

    Returns:
        MLflow run_id string
    """
    MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Load features
    X, metadata = load_all_features()
    n_scenes, n_features = X.shape

    # MLflow setup
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"\n🚀 MLflow run started: {run_id[:8]}...")

        # ── Log parameters ────────────────────────────────────────────
        mlflow.log_params({
            "model_type": "IsolationForest",
            "contamination": contamination,
            "n_estimators": n_estimators,
            "max_samples": max_samples,
            "random_state": random_state,
            "n_scenes": n_scenes,
            "n_features": n_features,
            "feature_names": str(FEATURE_NAMES),
        })

        # ── Build pipeline: scaler + model ────────────────────────────
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", IsolationForest(
                contamination=contamination,
                n_estimators=n_estimators,
                max_samples=max_samples,
                random_state=random_state,
            ))
        ])

        # ── Train ─────────────────────────────────────────────────────
        pipeline.fit(X)
        scores = pipeline.decision_function(X)
        predictions = pipeline.predict(X)  # -1 = anomaly, 1 = normal

        n_anomalies = int(np.sum(predictions == -1))
        n_normal = int(np.sum(predictions == 1))
        anomaly_rate = float(n_anomalies / n_scenes * 100)

        # ── Log metrics ───────────────────────────────────────────────
        mlflow.log_metrics({
            "n_scenes_trained": float(n_scenes),
            "n_anomalies_detected": float(n_anomalies),
            "n_normal_scenes": float(n_normal),
            "anomaly_rate_pct": anomaly_rate,
            "mean_anomaly_score": float(np.mean(scores)),
            "min_anomaly_score": float(np.min(scores)),
            "max_anomaly_score": float(np.max(scores)),
        })

        # ── Log scene-level results as artifact ───────────────────────
        results = []
        for i, m in enumerate(metadata):
            results.append({
                "scene": m["scene"],
                "computed_at": m["computed_at"],
                "anomaly_score": float(scores[i]),
                "prediction": "anomaly" if predictions[i] == -1 else "normal",
            })

        results_path = MODELS_DIR / "scene_predictions.json"
        results_path.write_text(json.dumps(results, indent=2))
        mlflow.log_artifact(str(results_path))

        # ── Log feature stats as artifact ─────────────────────────────
        feature_stats = {
            name: {
                "mean": float(np.mean(X[:, i])),
                "std": float(np.std(X[:, i])),
                "min": float(np.min(X[:, i])),
                "max": float(np.max(X[:, i])),
            }
            for i, name in enumerate(FEATURE_NAMES)
        }
        stats_path = MODELS_DIR / "feature_stats.json"
        stats_path.write_text(json.dumps(feature_stats, indent=2))
        mlflow.log_artifact(str(stats_path))

        # ── Log model to MLflow ───────────────────────────────────────
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="model",
            registered_model_name="geosentinel-anomaly-detector",
        )

        # ── Print summary ─────────────────────────────────────────────
        print(f"\n📊 Training Results:")
        print(f"   Scenes trained on : {n_scenes}")
        print(f"   Normal scenes     : {n_normal}")
        print(f"   Anomalies flagged : {n_anomalies}  ({anomaly_rate:.1f}%)")
        print(f"   Mean score        : {np.mean(scores):.6f}")
        print(f"\n📋 Scene predictions:")
        for r in results:
            flag = "🚨" if r["prediction"] == "anomaly" else "✅"
            print(f"   {flag} {r['scene']}: score={r['anomaly_score']:.4f}")
        print(f"\n✅ Model registered: geosentinel-anomaly-detector")
        print(f"   Run ID: {run_id}")
        print(f"   Tracking URI: {MLFLOW_TRACKING_URI}")

        return run_id


if __name__ == "__main__":
    run_id = train(
        contamination=0.05,
        n_estimators=100,
        random_state=42,
    )
    print(f"\n🎯 Done. Run ID: {run_id}")
    print(f"   View UI: mlflow ui --backend-store-uri {MLFLOW_TRACKING_URI}")
