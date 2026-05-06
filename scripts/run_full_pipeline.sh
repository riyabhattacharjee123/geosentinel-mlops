#!/bin/bash
# run_full_pipeline.sh
# Full pipeline: drift check → retrain if needed → promote model
# Usage: bash scripts/run_full_pipeline.sh

set -e
REPO="/workspaces/geosentinel-mlops"
DRIFT_THRESHOLD=0.30
cd "$REPO"

echo "=================================================="
echo "🛰️  GeoSentinel — Full MLOps Pipeline"
echo "=================================================="

# ── Step 1: Drift Detection ───────────────────────────
echo ""
echo "📊 Step 1: Running drift detection..."

DRIFT_RESULT=$(python -c "
import sys, json
sys.path.insert(0, '$REPO')
from src.monitoring.drift_detector import run_drift_check
result = run_drift_check()
print(json.dumps(result))
" 2>/dev/null | tail -1)

DRIFT_SCORE=$(echo "$DRIFT_RESULT" | python -c "import sys,json; print(json.load(sys.stdin)['drift_score'])")
IS_DRIFTED=$(echo "$DRIFT_RESULT" | python -c "import sys,json; print(json.load(sys.stdin)['is_drifted'])")
DRIFTED_FEATURES=$(echo "$DRIFT_RESULT" | python -c "import sys,json; print(', '.join(json.load(sys.stdin)['drifted_features']) or 'none')")
HTML_REPORT=$(echo "$DRIFT_RESULT" | python -c "import sys,json; print(json.load(sys.stdin)['html_report'])")

echo "   Drift score      : $DRIFT_SCORE"
echo "   Drifted features : $DRIFTED_FEATURES"
echo "   HTML report      : $HTML_REPORT"

# ── Step 2: Decide ────────────────────────────────────
echo ""
NEEDS_RETRAIN=$(python -c "print('yes' if $DRIFT_SCORE >= $DRIFT_THRESHOLD or '$IS_DRIFTED' == 'True' else 'no')")

if [ "$NEEDS_RETRAIN" = "no" ]; then
    echo "✅ Drift score $DRIFT_SCORE is below threshold $DRIFT_THRESHOLD"
    echo "   No retraining needed. Model is healthy."
    echo ""
    echo "=================================================="
    echo "✅ Pipeline complete — no action required"
    echo "=================================================="
    exit 0
fi

echo "🚨 Drift detected! Score $DRIFT_SCORE >= threshold $DRIFT_THRESHOLD"
echo "   Triggering retraining pipeline..."

# ── Step 3: Download latest data ─────────────────────
echo ""
echo "⬇️  Step 2: Downloading latest Sentinel-2 scenes..."
YEAR=$(date +%Y)
MONTH=$(date +%-m)

python -c "
import sys
sys.path.insert(0, '$REPO')
from src.ingestion.download_aws import list_scenes, download_ndvi_bands
from src.ingestion.compute_ndvi import compute_ndvi

scenes = list_scenes('32', 'U', 'MA', $YEAR, $MONTH)
if not scenes:
    print('  No scenes found for current month, skipping download')
else:
    for scene in scenes[:2]:
        paths = download_ndvi_bands(scene)
        scene_dir = list(paths.values())[0].parent
        compute_ndvi(scene_dir)
    print(f'  Downloaded and processed {min(2, len(scenes))} new scenes')
"

# ── Step 4: Retrain ───────────────────────────────────
echo ""
echo "🔄 Step 3: Retraining model..."
RUN_ID=$(python -c "
import sys
sys.path.insert(0, '$REPO')
from src.training.train import train
run_id = train(contamination=0.05, n_estimators=100, random_state=42)
print(run_id)
" 2>/dev/null | tail -1)
echo "   Training complete. Run ID: $RUN_ID"

# ── Step 5: Promote ───────────────────────────────────
echo ""
echo "🚀 Step 4: Promoting new model to Staging..."
python -c "
import sys, mlflow
sys.path.insert(0, '$REPO')
mlflow.set_tracking_uri('sqlite:////$REPO/mlflow/mlflow.db')
client = mlflow.tracking.MlflowClient()
versions = client.search_model_versions(\"name='geosentinel-anomaly-detector'\")
latest = max(versions, key=lambda v: int(v.version))
client.transition_model_version_stage(
    name='geosentinel-anomaly-detector',
    version=latest.version,
    stage='Staging',
    archive_existing_versions=True,
)
print(f'   Version {latest.version} promoted to Staging')
"

# ── Summary ───────────────────────────────────────────
echo ""
echo "=================================================="
echo "🎉 Pipeline complete — model retrained and promoted"
echo "=================================================="
echo "   Drift score  : $DRIFT_SCORE"
echo "   MLflow run   : $RUN_ID"
echo "   Drift report : $HTML_REPORT"
echo "=================================================="
