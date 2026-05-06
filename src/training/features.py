# src/training/features.py
"""
Extract ML features from NDVI stats JSON files.

Each stats JSON = one observation (one scene, one date).
We build a feature vector from the NDVI statistics that
the anomaly detection model will learn from.
"""

import json
import numpy as np
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def extract_features(stats: dict) -> np.ndarray:
    """
    Convert a single NDVI stats dict into a feature vector.

    Features used:
      - ndvi_mean       : average vegetation signal
      - ndvi_std        : variability across the tile
      - ndvi_min        : lowest value (water/shadow indicator)
      - ndvi_max        : highest value (dense vegetation indicator)
      - vegetation_pct  : % pixels with NDVI > 0.3
      - water_pct       : % pixels with NDVI < 0.0
      - bare_soil_pct   : % pixels with NDVI 0.0-0.1

    Returns:
        np.ndarray of shape (7,)
    """
    return np.array([
        stats["ndvi_mean"],
        stats["ndvi_std"],
        stats["ndvi_min"],
        stats["ndvi_max"],
        stats["vegetation_pct"],
        stats["water_pct"],
        stats["bare_soil_pct"],
    ], dtype=np.float32)


FEATURE_NAMES = [
    "ndvi_mean",
    "ndvi_std",
    "ndvi_min",
    "ndvi_max",
    "vegetation_pct",
    "water_pct",
    "bare_soil_pct",
]


def load_all_features(processed_dir: Path = PROCESSED_DIR) -> tuple:
    """
    Load all NDVI stats JSON files and return feature matrix + metadata.

    Returns:
        X        : np.ndarray of shape (n_scenes, 7)
        metadata : list of dicts with scene name and date
    """
    json_files = sorted(processed_dir.glob("*_NDVI_stats.json"))

    if not json_files:
        raise FileNotFoundError(
            f"No NDVI stats JSON files found in {processed_dir}\n"
            "Run compute_ndvi.py first."
        )

    X, metadata = [], []
    for f in json_files:
        stats = json.loads(f.read_text())
        X.append(extract_features(stats))
        metadata.append({
            "scene": stats["scene"],
            "computed_at": stats["computed_at"],
            "file": str(f),
        })

    print(f"✅ Loaded {len(X)} scene(s) — feature matrix shape: ({len(X)}, {len(FEATURE_NAMES)})")
    return np.array(X), metadata


if __name__ == "__main__":
    X, meta = load_all_features()
    print("\nFeature matrix:")
    for i, (row, m) in enumerate(zip(X, meta)):
        print(f"  Scene {i+1}: {m['scene']}")
        for name, val in zip(FEATURE_NAMES, row):
            print(f"    {name:<20}: {val:.6f}")
