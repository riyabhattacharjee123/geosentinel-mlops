#!/bin/bash
# run_drift_report.sh
# Runs drift detection and prints the full report summary
# Usage: bash scripts/run_drift_report.sh

set -e

REPO="/workspaces/geosentinel-mlops"
cd "$REPO"

echo "=================================================="
echo "🛰️  GeoSentinel — Drift Detection Report"
echo "=================================================="
echo ""

# Option 1: Via API (if Docker stack is running)
API_UP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

if [ "$API_UP" = "200" ]; then
    echo "📡 API detected — running drift check via endpoint..."
    echo ""
    curl -s -X POST http://localhost:8000/drift/check | python -m json.tool
    echo ""
    echo "✅ Report saved to: data/drift_reports/"
    echo ""
    LATEST=$(ls -t "$REPO/data/drift_reports/"*.json 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "📄 Latest report: $LATEST"
        echo ""
        echo "--- Full JSON ---"
        cat "$LATEST"
    fi

else
    echo "🐍 API not running — running drift check directly via Python..."
    echo ""
    python -c "
import sys, json
sys.path.insert(0, '$REPO')
from src.monitoring.drift_detector import run_drift_check

result = run_drift_check()

print()
print('=' * 50)
print('📊 DRIFT REPORT SUMMARY')
print('=' * 50)
print(f\"  Report name  : {result['report_name']}\")
print(f\"  Generated at : {result['generated_at']}\")
print(f\"  Reference    : {result['n_reference']} scenes\")
print(f\"  Current      : {result['n_current']} scenes\")
print()

status = '🚨 DRIFT DETECTED' if result['is_drifted'] else '✅ No significant drift'
print(f\"  Status       : {status}\")
print(f\"  Drift score  : {result['drift_score']:.4f}  (threshold: 0.30)\")
print()

if result['drifted_features']:
    print(f\"  Drifted features:\")
    for f in result['drifted_features']:
        print(f\"    ⚠️  {f}\")
else:
    print('  Drifted features : none')

print()
print(f\"  HTML report  : {result['html_report']}\")
print(f\"  JSON report  : {result['html_report'].replace('.html', '.json')}\")
print('=' * 50)

if result['is_drifted']:
    print()
    print('⚡ ACTION REQUIRED: Trigger retraining with:')
    print('   python src/training/train.py')
    print('   python src/training/promote_model.py --version <new_version> --stage Staging')
"
fi

echo ""
echo "📁 All drift reports:"
ls -lh "$REPO/data/drift_reports/" 2>/dev/null || echo "  No reports yet."
