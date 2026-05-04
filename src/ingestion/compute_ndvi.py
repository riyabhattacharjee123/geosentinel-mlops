# src/ingestion/compute_ndvi.py
"""
Compute NDVI from Sentinel-2 B04 (Red) and B08 (NIR) bands.

NDVI = (B08 - B04) / (B08 + B04)

Value interpretation:
  < 0.0   : Water, snow, clouds
  0.0-0.1 : Bare soil, rock, sand
  0.1-0.3 : Sparse vegetation / shrubland
  0.3-0.6 : Moderate vegetation / grassland
  0.6-0.8 : Dense healthy vegetation / forest
  > 0.8   : Very dense canopy (rare)
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path
import json
from datetime import datetime

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def compute_ndvi(scene_dir: Path, output_dir: Path = PROCESSED_DIR) -> Path:
    """
    Compute NDVI for a scene and save as GeoTIFF + stats JSON.

    Args:
        scene_dir:  Path to scene folder containing B04.tif and B08.tif
        output_dir: Where to save the NDVI output

    Returns:
        Path to the output NDVI GeoTIFF
    """
    b04_path = scene_dir / "B04.tif"
    b08_path = scene_dir / "B08.tif"

    if not b04_path.exists() or not b08_path.exists():
        raise FileNotFoundError(
            f"Missing bands in {scene_dir}. Expected B04.tif and B08.tif."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    scene_name = scene_dir.name
    ndvi_path = output_dir / f"{scene_name}_NDVI.tif"
    stats_path = output_dir / f"{scene_name}_NDVI_stats.json"

    print(f"📡 Computing NDVI for: {scene_name}")

    # Read bands
    with rasterio.open(b04_path) as b04_src:
        b04 = b04_src.read(1).astype("float32")
        profile = b04_src.profile.copy()
        print(f"  B04 shape: {b04.shape}  |  dtype: {b04.dtype}")

    with rasterio.open(b08_path) as b08_src:
        b08 = b08_src.read(1).astype("float32")
        print(f"  B08 shape: {b08.shape}  |  dtype: {b08.dtype}")

    # Compute NDVI — suppress divide-by-zero warnings
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(
            (b08 + b04) == 0,
            0.0,
            (b08 - b04) / (b08 + b04),
        )

    # Clip to valid range [-1, 1]
    ndvi = np.clip(ndvi, -1.0, 1.0)

    # Save NDVI GeoTIFF
    profile.update(dtype="float32", count=1, nodata=-9999)
    with rasterio.open(ndvi_path, "w", **profile) as dst:
        dst.write(ndvi, 1)

    print(f"  ✅ NDVI saved: {ndvi_path}")

    # Compute and save statistics
    valid_pixels = ndvi[ndvi != -9999]
    stats = {
        "scene": scene_name,
        "computed_at": datetime.utcnow().isoformat(),
        "ndvi_min": float(np.min(valid_pixels)),
        "ndvi_max": float(np.max(valid_pixels)),
        "ndvi_mean": float(np.mean(valid_pixels)),
        "ndvi_std": float(np.std(valid_pixels)),
        "pixel_count": int(valid_pixels.size),
        "vegetation_pct": float(np.sum(valid_pixels > 0.3) / valid_pixels.size * 100),
        "water_pct": float(np.sum(valid_pixels < 0.0) / valid_pixels.size * 100),
        "bare_soil_pct": float(np.sum((valid_pixels >= 0.0) & (valid_pixels < 0.1)) / valid_pixels.size * 100),
    }

    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"  ✅ Stats saved: {stats_path}")
    print_stats(stats)

    return ndvi_path


def print_stats(stats: dict) -> None:
    """Pretty print NDVI statistics."""
    print()
    print("  📊 NDVI Statistics:")
    print(f"     Mean NDVI   : {stats['ndvi_mean']:.4f}")
    print(f"     Min / Max   : {stats['ndvi_min']:.4f} / {stats['ndvi_max']:.4f}")
    print(f"     Std Dev     : {stats['ndvi_std']:.4f}")
    print(f"     Vegetation  : {stats['vegetation_pct']:.1f}%  (NDVI > 0.3)")
    print(f"     Water       : {stats['water_pct']:.1f}%  (NDVI < 0.0)")
    print(f"     Bare soil   : {stats['bare_soil_pct']:.1f}%  (NDVI 0.0–0.1)")
    print()


if __name__ == "__main__":
    print("🌿 GeoSentinel - NDVI Computation")
    print("=" * 50)

    # Find all scene folders in data/raw/
    scene_dirs = [d for d in RAW_DATA_DIR.iterdir() if d.is_dir()]

    if not scene_dirs:
        print("❌ No scene folders found in data/raw/")
        print("   Run download_aws.py first.")
        exit(1)

    print(f"Found {len(scene_dirs)} scene(s) to process:\n")
    for scene_dir in sorted(scene_dirs):
        compute_ndvi(scene_dir)
