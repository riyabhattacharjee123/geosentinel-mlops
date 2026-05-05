# src/ingestion/bulk_download.py
"""
Bulk download Sentinel-2 L2A scenes and compute NDVI for each.
Year, month, and scene count are all input parameters — nothing hardcoded.

Usage examples:
  # Download 20 scenes spread across a full year
  python bulk_download.py --year 2024 --scenes-per-month 2

  # Download from specific months only
  python bulk_download.py --year 2024 --months 3 4 5 6 7 8 9 --scenes-per-month 3

  # Single month, many scenes
  python bulk_download.py --year 2024 --months 6 --scenes-per-month 20

  # Multi-year
  python bulk_download.py --year 2023 2024 --scenes-per-month 2
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion.download_aws import list_scenes, download_ndvi_bands
from src.ingestion.compute_ndvi import compute_ndvi


def bulk_download(
    years: list[int],
    months: list[int],
    scenes_per_month: int,
    utm_zone: str,
    lat_band: str,
    square: str,
    skip_existing: bool,
) -> list[Path]:
    """
    Download scenes and compute NDVI for each.

    Args:
        years            : list of years e.g. [2023, 2024]
        months           : list of months e.g. [3, 4, 5, 6, 7, 8, 9, 10]
        scenes_per_month : how many scenes to download per month
        utm_zone         : UTM zone e.g. '32'
        lat_band         : latitude band e.g. 'U'
        square           : 100km square e.g. 'MA' (Frankfurt)
        skip_existing    : skip download if NDVI already computed

    Returns:
        List of NDVI output file paths
    """
    processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
    total_planned = len(years) * len(months) * scenes_per_month
    completed = 0
    skipped = 0
    failed = 0
    ndvi_outputs = []

    print("=" * 60)
    print("🛰️  GeoSentinel Bulk Downloader")
    print("=" * 60)
    print(f"  Tile        : {utm_zone}/{lat_band}/{square}")
    print(f"  Years       : {years}")
    print(f"  Months      : {months}")
    print(f"  Per month   : {scenes_per_month}")
    print(f"  Total target: {total_planned} scenes")
    print("=" * 60)

    for year in years:
        for month in months:
            print(f"\n📅 {year}/{month:02d}")

            try:
                scenes = list_scenes(utm_zone, lat_band, square, year, month)
            except Exception as e:
                print(f"  ⚠️  Could not list scenes: {e}")
                failed += 1
                continue

            if not scenes:
                print(f"  ⚠️  No scenes available for {year}/{month:02d}")
                continue

            # Take up to scenes_per_month from available scenes
            selected = scenes[:scenes_per_month]
            print(f"  Found {len(scenes)} scenes — downloading {len(selected)}")

            for scene_prefix in selected:
                scene_name = scene_prefix.rstrip("/").split("/")[-1]
                ndvi_path = processed_dir / f"{scene_name}_NDVI.tif"

                # Skip if already processed
                if skip_existing and ndvi_path.exists():
                    print(f"  ⏭️  Already processed: {scene_name}")
                    skipped += 1
                    ndvi_outputs.append(ndvi_path)
                    continue

                try:
                    # Download bands
                    paths = download_ndvi_bands(scene_prefix)
                    scene_dir = list(paths.values())[0].parent

                    # Compute NDVI
                    out = compute_ndvi(scene_dir)
                    ndvi_outputs.append(out)
                    completed += 1

                except Exception as e:
                    print(f"  ❌ Failed: {scene_name} — {e}")
                    failed += 1
                    continue

    # Summary
    print("\n" + "=" * 60)
    print("📊 Bulk Download Summary")
    print("=" * 60)
    print(f"  ✅ Completed : {completed}")
    print(f"  ⏭️  Skipped   : {skipped}")
    print(f"  ❌ Failed    : {failed}")
    print(f"  📁 Total NDVI files: {len(ndvi_outputs)}")
    print("=" * 60)

    return ndvi_outputs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bulk download Sentinel-2 scenes and compute NDVI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 20 scenes across 2024 (2 per month, all 12 months)
  python bulk_download.py --year 2024 --scenes-per-month 2

  # 20 scenes from summer months only
  python bulk_download.py --year 2024 --months 5 6 7 8 9 --scenes-per-month 4

  # Multi-year, 1 per month
  python bulk_download.py --year 2023 2024 --scenes-per-month 1

  # Different tile (Berlin = 33UUU)
  python bulk_download.py --year 2024 --utm-zone 33 --lat-band U --square UU
        """
    )

    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        required=True,
        help="Year(s) to download. e.g. --year 2024 or --year 2023 2024"
    )
    parser.add_argument(
        "--months",
        type=int,
        nargs="+",
        default=list(range(1, 13)),
        help="Months to include (1-12). Default: all 12 months"
    )
    parser.add_argument(
        "--scenes-per-month",
        type=int,
        default=2,
        help="How many scenes to download per month. Default: 2"
    )
    parser.add_argument(
        "--utm-zone",
        type=str,
        default="32",
        help="UTM zone. Default: 32 (Frankfurt/Rhine-Main)"
    )
    parser.add_argument(
        "--lat-band",
        type=str,
        default="U",
        help="Latitude band letter. Default: U"
    )
    parser.add_argument(
        "--square",
        type=str,
        default="MA",
        help="100km square identifier. Default: MA (Frankfurt)"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        default=False,
        help="Re-download and recompute even if NDVI already exists"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    ndvi_files = bulk_download(
        years=args.year,
        months=args.months,
        scenes_per_month=args.scenes_per_month,
        utm_zone=args.utm_zone,
        lat_band=args.lat_band,
        square=args.square,
        skip_existing=not args.no_skip,
    )

    print(f"\n🎯 Ready to train. Run:")
    print(f"   python src/training/train.py")
