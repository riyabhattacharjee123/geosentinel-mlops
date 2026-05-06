# airflow/dags/retrain_pipeline.py
"""
Auto-retraining DAG — triggered when drift is detected.

Flow:
  check_drift → [if drifted] → download_new_data → retrain → promote_model
              → [if clean]   → log_status (skip retraining)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/workspaces/geosentinel-mlops")

default_args = {
    "owner": "geosentinel",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

DRIFT_THRESHOLD = 0.3   # retrain if >30% of features drift


def task_check_drift(**context):
    """Run drift detection and decide whether to retrain."""
    from src.monitoring.drift_detector import run_drift_check

    result = run_drift_check()
    drift_score = result["drift_score"]
    is_drifted  = result["is_drifted"]

    context["ti"].xcom_push(key="drift_score",    value=drift_score)
    context["ti"].xcom_push(key="drift_report",   value=result["report_name"])
    context["ti"].xcom_push(key="drifted_features", value=result["drifted_features"])

    print(f"Drift score: {drift_score:.4f} | Threshold: {DRIFT_THRESHOLD}")
    print(f"Drifted features: {result['drifted_features']}")

    if drift_score >= DRIFT_THRESHOLD or is_drifted:
        print("🚨 Drift detected — triggering retraining")
        return "download_new_data"
    else:
        print("✅ No significant drift — skipping retraining")
        return "no_retraining_needed"


def task_download_new_data(**context):
    """Download the latest available scenes."""
    from src.ingestion.download_aws import list_scenes, download_ndvi_bands
    from src.ingestion.compute_ndvi import compute_ndvi

    exec_date = context["execution_date"]
    year, month = exec_date.year, exec_date.month

    print(f"📡 Downloading new scenes for {year}/{month:02d}...")
    scenes = list_scenes("32", "U", "MA", year, month)

    if not scenes:
        raise ValueError(f"No scenes found for {year}/{month}")

    # Download 2 new scenes
    downloaded = 0
    for scene_prefix in scenes[:2]:
        paths = download_ndvi_bands(scene_prefix)
        scene_dir = list(paths.values())[0].parent
        compute_ndvi(scene_dir)
        downloaded += 1

    print(f"✅ Downloaded and processed {downloaded} new scenes")
    context["ti"].xcom_push(key="new_scenes", value=downloaded)


def task_retrain(**context):
    """Retrain the model with all available data."""
    from src.training.train import train

    drift_score = context["ti"].xcom_pull(
        task_ids="check_drift", key="drift_score"
    )
    print(f"🔄 Retraining triggered by drift score: {drift_score:.4f}")

    run_id = train(
        contamination=0.05,
        n_estimators=100,
        random_state=42,
    )
    context["ti"].xcom_push(key="new_run_id", value=run_id)
    print(f"✅ Retraining complete. Run ID: {run_id}")


def task_promote(**context):
    """Promote the new model version to Staging."""
    import mlflow

    mlflow.set_tracking_uri(
        "sqlite:////workspaces/geosentinel-mlops/mlflow/mlflow.db"
    )
    client = mlflow.tracking.MlflowClient()

    # Get latest version
    versions = client.search_model_versions(
        "name='geosentinel-anomaly-detector'"
    )
    latest = max(versions, key=lambda v: int(v.version))

    client.transition_model_version_stage(
        name="geosentinel-anomaly-detector",
        version=latest.version,
        stage="Staging",
        archive_existing_versions=True,
    )
    print(f"✅ Model Version {latest.version} promoted to Staging")


def task_no_retraining(**context):
    drift_score = context["ti"].xcom_pull(
        task_ids="check_drift", key="drift_score"
    )
    print(f"✅ Drift score {drift_score:.4f} below threshold {DRIFT_THRESHOLD}")
    print("   No retraining needed this cycle.")


with DAG(
    dag_id="geosentinel_auto_retrain",
    description="Auto-retrain when data drift is detected",
    default_args=default_args,
    start_date=datetime(2024, 6, 1),
    schedule_interval="0 8 * * 1",   # every Monday at 08:00 UTC
    catchup=False,
    tags=["geosentinel", "mlops", "retraining", "drift"],
) as dag:

    check_drift = BranchPythonOperator(
        task_id="check_drift",
        python_callable=task_check_drift,
    )

    download_new_data = PythonOperator(
        task_id="download_new_data",
        python_callable=task_download_new_data,
    )

    retrain = PythonOperator(
        task_id="retrain",
        python_callable=task_retrain,
    )

    promote = PythonOperator(
        task_id="promote_model",
        python_callable=task_promote,
    )

    no_retraining = PythonOperator(
        task_id="no_retraining_needed",
        python_callable=task_no_retraining,
    )

    check_drift >> [download_new_data, no_retraining]
    download_new_data >> retrain >> promote
