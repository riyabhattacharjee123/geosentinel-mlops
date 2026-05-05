# src/ingestion/compute_ndvi.py
"""
Compute NDVI from Sentinel-2 B04 (Red) and B08 (NIR) bands.
Reads at reduced resolution using COG overviews to save memory.

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
from rasterio.enums import Resampling
from pathlib import Path
import json
from datetime import datetime

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# Read at 1/10 resolution — enough for statistics, uses ~5MB instead of 460MB
OVERVIEW_LEVEL = 10


def read_band_downsampled(path: Path, overview_level: int) -> np.ndarray:
    """Read a GeoTIFF band at reduced resolution using COG overviews."""
    with rasterio.open(path) as src:
        full_h, full_w = src.height, src.width
        out_h = full_h // overview_level
        out_w = full_w // overview_level
        data = src.read(
            1,
            out_shape=(out_h, out_w),
            resampling=Resampling.average,
        ).astype("float32")
    return data


def compute_ndvi(scene_dir: Path, output_dir: Path = PROCESSED_DIR) -> Path:
    """
    Compute NDVI for a scene and save as GeoTIFF + stats JSON.

    Args:
        scene_dir:  Path to scene folder containing B04.tif and B08.tif
        output_dir: Where to save the NDVI output

    Returns:
        Path to the output NDVI stats JSON
    """
    b04_path = scene_dir / "B04.tif"
    b08_path = scene_dir / "B08.tif"

    if not b04_path.exists() or not b08_path.exists():
        raise FileNotFoundError(
            f"Missing bands in {scene_dir}. Expected B04.tif and B08.tif."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    scene_name = scene_dir.name
    stats_path = output_dir / f"{scene_name}_NDVI_stats.json"

    if stats_path.exists():
        print(f"  ⏭️  Stats already exist: {scene_name}")
        return stats_path

    print(f"📡 Computing NDVI for: {scene_name}")

    # Read bands at reduced resolution
    b04 = read_band_downsampled(b04_path, OVERVIEW_LEVEL)
    b08 = read_band_downsampled(b08_path, OVERVIEW_LEVEL)
    print(f"  Shape: {b04.shape}  |  Memory: ~{b04.nbytes / 1e6:.1f} MB per band")

    # Compute NDVI
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(
            (b08 + b04) == 0,
            np.nan,
            (b08 - b04) / (b08 + b04),
        )

    ndvi = np.clip(ndvi, -1.0, 1.0)
    valid = ndvi[~np.isnan(ndvi)]

    # Compute stats
    stats = {
        "scene": scene_name,
        "computed_at": datetime.utcnow().isoformat(),
        "resolution_factor": OVERVIEW_LEVEL,
        "ndvi_min": float(np.min(valid)),
        "ndvi_max": float(np.max(valid)),
        "ndvi_mean": float(np.mean(valid)),
        "ndvi_std": float(np.std(valid)),
        "pixel_count": int(valid.size),
        "vegetation_pct": float(np.sum(valid > 0.3) / valid.size * 100),
        "water_pct": float(np.sum(valid < 0.0) / valid.size * 100),
        "bare_soil_pct": float(np.sum((valid >= 0.0) & (valid < 0.1)) / valid.size * 100),
    }

    stats_path.write_text(json.dumps(stats, indent=2))
    print(f"  ✅ Stats saved: {stats_path.name}")
    print(f"     NDVI mean={stats['ndvi_mean']:.3f}  "
          f"veg={stats['vegetation_pct']:.1f}%  "
          f"water={stats['water_pct']:.1f}%  "
          f"soil={stats['bare_soil_pct']:.1f}%")

    return stats_path


if __name__ == "__main__":
    print("🌿 GeoSentinel - NDVI Computation")
    print("=" * 50)
    scene_dirs = [d for d in RAW_DATA_DIR.iterdir() if d.is_dir()]
    if not scene_dirs:
        print("❌ No scene folders found in data/raw/")
        exit(1)
    for scene_dir in sorted(scene_dirs):
        compute_ndvi(scene_dir)
