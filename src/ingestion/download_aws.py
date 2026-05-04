# src/ingestion/download_aws.py
"""
Download Sentinel-2 L2A bands from the AWS Open Data Registry.
No credentials required - data is publicly available.

Bucket: sentinel-cogs (eu-central-1)
Path structure: sentinel-s2-l2a-cogs/{utm_zone}/{lat_band}/{square}/{year}/{month}/{scene}/

NDVI requires only two bands:
  - B04.tif  (Red,         10m resolution)
  - B08.tif  (Near-Infrared, 10m resolution)

NDVI = (B08 - B04) / (B08 + B04)
Values range from -1 to +1. Healthy vegetation = 0.3 to 0.8
"""

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path

# AWS bucket config - no auth needed
BUCKET = "sentinel-cogs"
REGION = "eu-central-1"
BASE_PREFIX = "sentinel-s2-l2a-cogs"

# Default output directory
RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def get_s3_client():
    """Create an anonymous S3 client for public bucket access."""
    return boto3.client(
        "s3",
        region_name=REGION,
        config=Config(signature_version=UNSIGNED),
    )


def list_scenes(
    utm_zone: str = "32",
    lat_band: str = "U",
    square: str = "MA",
    year: int = 2024,
    month: int = 6,
) -> list[str]:
    """
    List all available Sentinel-2 L2A scenes for a given tile and month.

    UTM tile 32UMA covers Frankfurt/Rhine-Main area.
    Find your tile at: https://maps.eorc.jaxa.jp/tiles/

    Args:
        utm_zone: UTM zone number e.g. '32'
        lat_band: Latitude band letter e.g. 'U'
        square:   100km square identifier e.g. 'MA'
        year:     Year e.g. 2024
        month:    Month as integer e.g. 6

    Returns:
        List of S3 prefix strings for each scene
    """
    s3 = get_s3_client()
    prefix = f"{BASE_PREFIX}/{utm_zone}/{lat_band}/{square}/{year}/{month}/"

    response = s3.list_objects_v2(
        Bucket=BUCKET,
        Prefix=prefix,
        Delimiter="/",
    )

    scenes = [p["Prefix"] for p in response.get("CommonPrefixes", [])]
    print(f"✅ Found {len(scenes)} scenes under {prefix}")
    return scenes


def download_ndvi_bands(
    scene_prefix: str,
    output_dir: Path = RAW_DATA_DIR,
    bands: list[str] = ["B04.tif", "B08.tif"],
) -> dict[str, Path]:
    """
    Download NDVI-relevant bands for a given scene.

    Args:
        scene_prefix: S3 prefix string from list_scenes()
                      e.g. 'sentinel-s2-l2a-cogs/32/U/MA/2024/6/S2A_32UMA_20240602_0_L2A/'
        output_dir:   Local directory to save files (default: data/raw/)
        bands:        List of band filenames to download

    Returns:
        Dict mapping band name to local file path e.g. {'B04.tif': Path(...)}
    """
    s3 = get_s3_client()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use scene name as subfolder to keep multiple scenes organised
    scene_name = scene_prefix.rstrip("/").split("/")[-1]
    scene_dir = output_dir / scene_name
    scene_dir.mkdir(parents=True, exist_ok=True)

    downloaded = {}

    for band in bands:
        key = f"{scene_prefix}{band}"
        outfile = scene_dir / band

        if outfile.exists():
            print(f"⏭️  Already exists, skipping: {outfile.name}")
            downloaded[band] = outfile
            continue

        print(f"⬇️  Downloading {band} from {scene_name}...")
        s3.download_file(BUCKET, key, str(outfile))
        size_mb = outfile.stat().st_size / 1e6
        print(f"✅ Saved: {outfile}  ({size_mb:.1f} MB)")
        downloaded[band] = outfile

    return downloaded


def download_scene_by_index(
    utm_zone: str = "32",
    lat_band: str = "U",
    square: str = "MA",
    year: int = 2024,
    month: int = 6,
    scene_index: int = 0,
) -> dict[str, Path]:
    """
    Convenience function: list scenes and download bands from one scene by index.

    Args:
        scene_index: 0 = most recent, -1 = oldest in the month

    Returns:
        Dict of downloaded band paths
    """
    scenes = list_scenes(utm_zone, lat_band, square, year, month)

    if not scenes:
        raise ValueError(f"No scenes found for {utm_zone}/{lat_band}/{square} {year}/{month}")

    scene = scenes[scene_index]
    print(f"\n📡 Selected scene: {scene.split('/')[-2]}")
    return download_ndvi_bands(scene)


if __name__ == "__main__":
    # Run directly to download first scene of June 2024 over Frankfurt
    print("🛰️  GeoSentinel - Sentinel-2 Band Downloader")
    print("=" * 50)

    # Step 1: list available scenes
    scenes = list_scenes(
        utm_zone="32",
        lat_band="U",
        square="MA",
        year=2024,
        month=6,
    )

    print("\nAvailable scenes:")
    for i, s in enumerate(scenes):
        print(f"  [{i}] {s.split('/')[-2]}")

    # Step 2: download B04 + B08 from the first scene
    print()
    paths = download_ndvi_bands(scenes[0])

    print("\n📁 Downloaded files:")
    for band, path in paths.items():
        print(f"  {band}: {path}  ({path.stat().st_size / 1e6:.1f} MB)")
