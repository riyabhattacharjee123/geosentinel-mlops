# src/monitoring/drift_detector.py
"""
Detect data drift in NDVI features using Evidently AI.
Compares current scene features against the training baseline.
Outputs a drift report + a simple drift score (0-1).
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from evidently.report import Report
from evidently.metrics import DataDriftTable, DatasetDriftMetric

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
REPORTS_DIR   = Path(__file__).resolve().parents[2] / "data" / "drift_reports"
BASELINE_PATH = Path(__file__).resolve().parents[2] / "models" / "feature_stats.json"

FEATURE_NAMES = [
    "ndvi_mean", "ndvi_std", "ndvi_min", "ndvi_max",
    "vegetation_pct", "water_pct", "bare_soil_pct",
]


def load_all_stats() -> pd.DataFrame:
    """Load all NDVI stats JSON files into a DataFrame."""
    rows = []
    for f in sorted(PROCESSED_DIR.glob("*_NDVI_stats.json")):
        stats = json.loads(f.read_text())
        rows.append({feat: stats[feat] for feat in FEATURE_NAMES})
    return pd.DataFrame(rows)


def detect_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    report_name: str = None,
) -> dict:
    """
    Run Evidently drift detection between reference and current data.

    Args:
        reference_df : training baseline features
        current_df   : new/recent features to compare
        report_name  : filename for the HTML report

    Returns:
        dict with drift_score, drifted_features, is_drifted
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report = Report(metrics=[
        DataDriftTable(),
        DatasetDriftMetric(),
    ])

    report.run(reference_data=reference_df, current_data=current_df)
    result = report.as_dict()
    
    # Extract drift metrics
    dataset_drift = result["metrics"][1]["result"]
    drift_score   = dataset_drift.get("share_of_drifted_columns", 0.0)
    is_drifted    = dataset_drift.get("dataset_drift", False)

    drifted_features = [
        col for col, data in result["metrics"][0]["result"]["drift_by_columns"].items()
        if data.get("drift_detected", False)
    ]

    # Save HTML report
    if report_name is None:
        report_name = f"drift_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    html_path = REPORTS_DIR / f"{report_name}.html"
    report.save_html(str(html_path))

    summary = {
        "report_name":       report_name,
        "generated_at":      datetime.utcnow().isoformat(),
        "drift_score":       round(drift_score, 4),
        "is_drifted":        is_drifted,
        "drifted_features":  drifted_features,
        "n_reference":       len(reference_df),
        "n_current":         len(current_df),
        "html_report":       str(html_path),
    }

    # Save JSON summary
    json_path = REPORTS_DIR / f"{report_name}.json"
    json_path.write_text(json.dumps(summary, indent=2))

    return summary


def run_drift_check(split_ratio: float = 0.7) -> dict:
    """
    Load all scenes, split into reference/current, run drift check.

    Args:
        split_ratio: fraction of scenes to use as reference baseline

    Returns:
        Drift summary dict
    """
    df = load_all_stats()

    if len(df) < 4:
        raise ValueError(f"Need at least 4 scenes for drift detection, got {len(df)}")

    split = int(len(df) * split_ratio)
    reference_df = df.iloc[:split].reset_index(drop=True)
    current_df   = df.iloc[split:].reset_index(drop=True)

    print(f"🔍 Running drift detection...")
    print(f"   Reference: {len(reference_df)} scenes")
    print(f"   Current  : {len(current_df)} scenes")

    summary = detect_drift(reference_df, current_df)

    status = "🚨 DRIFT DETECTED" if summary["is_drifted"] else "✅ No drift"
    print(f"\n{status}")
    print(f"   Drift score       : {summary['drift_score']:.4f}")
    print(f"   Drifted features  : {summary['drifted_features'] or 'none'}")
    print(f"   HTML report       : {summary['html_report']}")

    return summary


if __name__ == "__main__":
    result = run_drift_check()
    print(json.dumps(result, indent=2))
