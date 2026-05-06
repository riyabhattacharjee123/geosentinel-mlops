# src/training/promote_model.py
"""
Promote a registered MLflow model version to Production stage.

Stages in MLflow Model Registry:
  None       → just registered, not ready
  Staging    → candidate, under evaluation
  Production → live, this is what serving loads
  Archived   → retired, kept for history

Run this after reviewing training results and deciding
the new version is better than the current Production model.
"""

import argparse
import mlflow
from pathlib import Path

MLFLOW_TRACKING_URI = (
    f"sqlite:////workspaces/geosentinel-mlops/mlflow/mlflow.db"
)
MODEL_NAME = "geosentinel-anomaly-detector"


def list_versions(client: mlflow.tracking.MlflowClient) -> None:
    """Print all registered versions and their current stages."""
    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    print(f"\n📋 All versions of '{MODEL_NAME}':")
    for v in sorted(versions, key=lambda x: int(x.version)):
        icon = "🟢" if v.current_stage == "Production" else \
               "🟡" if v.current_stage == "Staging" else \
               "⚫" if v.current_stage == "Archived" else "⬜"
        print(f"  {icon} Version {v.version}  "
              f"stage={v.current_stage:<12}  "
              f"run_id={v.run_id[:8]}...")


def promote(version: str, stage: str) -> None:
    """Promote a model version to the given stage."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()

    # Show current state
    list_versions(client)

    # Promote
    print(f"\n🚀 Promoting Version {version} → {stage} ...")
    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=version,
        stage=stage,
        archive_existing_versions=True,
    )

    # Confirm
    info = client.get_model_version(MODEL_NAME, version)
    print(f"✅ Done.")
    print(f"   Model   : {MODEL_NAME}")
    print(f"   Version : {info.version}")
    print(f"   Stage   : {info.current_stage}")
    print(f"   Run ID  : {info.run_id}")

    # Show updated state
    list_versions(client)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Promote an MLflow model version to a stage"
    )
    parser.add_argument(
        "--version",
        type=str,
        default="2",
        help="Model version number to promote. Default: 2"
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="Production",
        choices=["Staging", "Production", "Archived"],
        help="Target stage. Default: Production"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    promote(version=args.version, stage=args.stage)
