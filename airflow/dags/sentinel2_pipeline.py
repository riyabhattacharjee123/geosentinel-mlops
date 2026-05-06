# airflow/dags/sentinel2_pipeline.py
"""
GeoSentinel Phase 1 Pipeline DAG

Runs daily and executes three tasks in sequence:
  1. download_bands   — fetch B04 + B08 from AWS Open Data
  2. compute_ndvi     — compute NDVI, save GeoTIFF + stats JSON
  3. version_data     — track new files with DVC

Schedule: daily at 06:00 UTC
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Make sure our src modules are importable inside Airflow
sys.path.insert(0, "/workspaces/geosentinel-mlops")

default_args = {
    "owner": "geosentinel",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ── Task functions ────────────────────────────────────────────────────────────

def task_download_bands(**context):
    """Download B04 + B08 for the most recent available scene."""
    from src.ingestion.download_aws import list_scenes, download_ndvi_bands

    # Use execution date to pick the right month
    exec_date = context["execution_date"]
    year = exec_date.year
    month = exec_date.month

    print(f"📡 Fetching scenes for {year}/{month:02d} ...")
    scenes = list_scenes(
        utm_zone="32",
        lat_band="U",
        square="MA",
        year=year,
        month=month,
    )

    if not scenes:
        raise ValueError(f"No scenes found for {year}/{month}")

    # Always grab the first (most recent returned) scene
    scene = scenes[0]
    print(f"Selected scene: {scene.split('/')[-2]}")

    paths = download_ndvi_bands(scene)

    # Push scene path to XCom so next task can find it
    scene_dir = str(list(paths.values())[0].parent)
    context["ti"].xcom_push(key="scene_dir", value=scene_dir)
    print(f"✅ Download complete. Scene dir: {scene_dir}")


def task_compute_ndvi(**context):
    """Compute NDVI from downloaded bands."""
    from src.ingestion.compute_ndvi import compute_ndvi
    from pathlib import Path

    # Pull scene_dir from previous task via XCom
    scene_dir = context["ti"].xcom_pull(
        task_ids="download_bands", key="scene_dir"
    )
    print(f"🌿 Computing NDVI for: {scene_dir}")

    ndvi_path = compute_ndvi(Path(scene_dir))
    context["ti"].xcom_push(key="ndvi_path", value=str(ndvi_path))
    print(f"✅ NDVI written to: {ndvi_path}")


def task_version_data(**context):
    """Track new data files with DVC."""
    import subprocess
    from pathlib import Path

    repo_root = "/workspaces/geosentinel-mlops"

    ndvi_path = context["ti"].xcom_pull(
        task_ids="compute_ndvi", key="ndvi_path"
    )
    print(f"📦 Versioning data with DVC ...")

    # Add both raw and processed dirs to DVC
    for data_dir in ["data/raw", "data/processed"]:
        result = subprocess.run(
            ["dvc", "add", data_dir],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"⚠️  DVC warning: {result.stderr}")

    # Git commit the updated .dvc metadata files
    subprocess.run(["git", "add", "data/raw.dvc", "data/processed.dvc", "data/.gitignore"],
                   cwd=repo_root)
    
    exec_date = context["execution_date"].strftime("%Y-%m-%d")
    subprocess.run(
        ["git", "commit", "-m", f"data: update DVC tracking for {exec_date}"],
        cwd=repo_root,
    )
    print("✅ DVC versioning complete.")


# ── DAG definition ────────────────────────────────────────────────────────────

with DAG(
    dag_id="sentinel2_ndvi_pipeline",
    description="Download Sentinel-2 bands, compute NDVI, version with DVC",
    default_args=default_args,
    start_date=datetime(2024, 6, 1),
    schedule_interval="0 6 * * *",   # daily at 06:00 UTC
    catchup=False,
    tags=["geosentinel", "sentinel-2", "ndvi", "mlops"],
) as dag:

    download = PythonOperator(
        task_id="download_bands",
        python_callable=task_download_bands,
    )

    ndvi = PythonOperator(
        task_id="compute_ndvi",
        python_callable=task_compute_ndvi,
    )

    version = PythonOperator(
        task_id="version_data",
        python_callable=task_version_data,
    )

    # Define execution order
    download >> ndvi >> version
