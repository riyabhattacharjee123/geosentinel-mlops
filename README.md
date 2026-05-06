# GeoSentinel-MLOps

> An end-to-end MLOps platform for Earth Observation — detecting vegetation anomalies using Sentinel-2 satellite data, deployed on Kubernetes with full model versioning, serving, drift monitoring, and automated retraining.

[![Project Status](https://img.shields.io/badge/status-complete-brightgreen)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![Phase](https://img.shields.io/badge/phase-4%20of%205-blue)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)

---

## Project Goal

Build a production-grade MLOps platform that:
- Ingests free Copernicus Sentinel-2 satellite imagery on a schedule
- Computes NDVI (vegetation index) and detects anomalies using ML
- Deploys the model as a REST API on Kubernetes
- Monitors model drift with automated retraining triggers
- Demonstrates the full MLOps lifecycle end-to-end for portfolio purposes

**Why this project?** This bridges DevOps/Platform Engineering with ML — leveraging real Earth Observation domain expertise (ESA/Copernicus) to build something rare: infrastructure-focused ML tooling for satellite data pipelines.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GeoSentinel MLOps                          │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 1 — Data Pipeline                                        │
│  AWS S3 (sentinel-cogs) → B04+B08 bands → NDVI computation     │
│  DVC versioning | Airflow DAG (daily @ 06:00 UTC)              │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 2 — Model Training                                       │
│  19 scenes → 7 NDVI features → Isolation Forest model          │
│  MLflow experiment tracking | Model Registry (Staging)          │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 3 — Serving                                              │
│  FastAPI REST API → Docker → Helm chart → Kubernetes (kind)    │
│  Endpoints: /health /model/info /predict /predict/batch         │
├─────────────────────────────────────────────────────────────────┤
│  PHASE 4 — Monitoring & Auto-Retraining                         │
│  Evidently AI drift reports | Prometheus /metrics endpoint      │
│  Grafana dashboard | Auto-retrain Airflow DAG (weekly)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Source | AWS Open Data Registry (Sentinel-2 L2A COGs) |
| Data Versioning | DVC |
| Experiment Tracking | MLflow 3.11.1 |
| Model Registry | MLflow Model Registry |
| Pipeline Orchestration | Apache Airflow 2.10.4 |
| Model Serving | FastAPI + Docker |
| Infrastructure | Kubernetes (kind → Oracle Cloud free tier) |
| IaC | Terraform + Helm |
| Drift Monitoring | Evidently AI |
| Metrics | Prometheus + Grafana |
| Language | Python 3.12 |

---

## Repository Structure

```
geosentinel-mlops/
├── src/
│   ├── ingestion/
│   │   ├── auth.py              # OAuth2 token generation (CDSE)
│   │   ├── search.py            # OData catalog search
│   │   ├── download_aws.py      # Sentinel-2 band downloader (AWS, no auth)
│   │   ├── compute_ndvi.py      # NDVI computation via COG overviews
│   │   └── bulk_download.py     # Parameterised bulk scene downloader
│   ├── training/
│   │   ├── features.py          # NDVI stats → 7-feature vector
│   │   ├── train.py             # Isolation Forest + MLflow tracking
│   │   └── promote_model.py     # Promote model to Staging/Production
│   ├── serving/
│   │   └── app.py               # FastAPI endpoint + Prometheus metrics
│   └── monitoring/
│       ├── drift_detector.py    # Evidently AI drift detection
│       └── metrics.py           # Prometheus metric definitions
├── airflow/
│   └── dags/
│       ├── sentinel2_pipeline.py   # Daily data ingestion DAG
│       └── retrain_pipeline.py     # Weekly auto-retraining DAG
├── data/
│   ├── raw/                     # Downloaded GeoTIFF bands (DVC-tracked)
│   ├── processed/               # NDVI stats JSON files (19 scenes)
│   └── drift_reports/           # Evidently HTML + JSON reports
├── mlflow/                      # MLflow tracking SQLite DB
├── mlruns/                      # MLflow artifact storage
├── models/                      # Scene predictions + feature stats
├── infra/
│   ├── helm/geosentinel/        # Kubernetes Helm chart
│   ├── prometheus/              # Prometheus scrape config
│   └── grafana/                 # Grafana datasource + dashboard provisioning
├── Dockerfile                   # Single-stage Python 3.12 image
├── docker-compose.yml           # Full stack: API + Prometheus + Grafana
├── requirements.txt             # Development dependencies
├── requirements-serving.txt     # Production serving dependencies
└── .env.example                 # Credential template
```

---

## 🗓️ Development Journal

### Day 1 — April 22, 2026
**Goal:** Research, planning, project bootstrap.

- Researched AI/ML impact on DevOps roles — decided on MLOps transition path
- Designed GeoSentinel-MLOps: NDVI anomaly detection leveraging ESA background
- Created GitHub repo, launched Codespace, set up folder structure
- Fixed branch naming: `Main` → `main`
- Written: `auth.py`, `search.py`, `download.py`
- **Key learning:** CDSE replaced SciHub. OData spatial queries use `OData.CSC.Intersects`

**Commit:** `feat: Phase 1 - Sentinel-2 ingestion pipeline`

---

### Day 2 — May 4, 2026
**Goal:** Complete Phase 1 — automated, versioned satellite data pipeline.

- CDSE OData API returned 403 — `sentinelsat` library uses deprecated SciHub endpoint
- Switched to **AWS Open Data Registry** (`sentinel-cogs` bucket) — no auth, same data
- Written: `download_aws.py` — lists and downloads B04+B08 bands (~20MB vs 800MB full zip)
- Written: `compute_ndvi.py` — COG overview reading at 1/10 resolution (5MB RAM vs 460MB)
- Written: `sentinel2_pipeline.py` Airflow DAG — `download_bands → compute_ndvi → version_data`
- First NDVI result: Frankfurt June 2024 — Mean=0.0276, Vegetation=0.6%, Soil=87.3%
- Fixed: Airflow `db init` → `db migrate`, pydantic-core conflict, DVC fsspec conflict

**All 3 DAG tasks green on first test run**

**Commit:** `feat: Phase 1 complete - Airflow DAG, NDVI pipeline, DVC tracking`

---

### Day 3 — May 5, 2026
**Goal:** Phase 2 — MLflow experiment tracking, anomaly detection model.

- Written: `features.py` — 7-feature vector from NDVI stats JSON
- **Run 1** (1 scene): Score=0.0 — not enough data
- Memory issue: 10980×10980 pixels × 146MB/band = Codespace crash
  - Fix: COG overview levels — `rasterio out_shape` downsamples to 1/10 resolution
- Written: `bulk_download.py` — fully parameterised (`--year`, `--months`, `--scenes-per-month`, `--utm-zone`)
- Downloaded 20 scenes: May–September 2024, tile 32/U/MA (Frankfurt)
- **Run 2** (19 scenes): 1 anomaly flagged — `S2A_32UMA_20240605_0_L2A` (score: -0.0062)
- Written: `promote_model.py` — parameterised staging with before/after version table
- MLflow UI launched at port 5000 via Codespace port forwarding

**Model Registry:**
```
Version 1 → Archived  (1 scene, outdated)
Version 2 → Staging   (19 scenes, current)
```

**Key learning:** MLflow `transition_model_version_stage` deprecated in 2.9.0 — will migrate to aliases in next iteration. Negative anomaly score = most isolated point in feature space.

**Commit:** `feat: Phase 2 complete - MLflow tracking, 19-scene anomaly model v2 in Staging`

---

### Day 4 — May 6, 2026
**Goal:** Phase 3 + Phase 4 — serving, monitoring, auto-retraining.

**Phase 3 — FastAPI + Docker + Helm:**
- Written: `src/serving/app.py` — FastAPI with `/health`, `/model/info`, `/predict`, `/predict/batch`, `/metrics`, `/drift/check`
- Containerised with Docker (single-stage, non-root user, healthcheck)
- Fixed: `pkg_resources` missing → added `setuptools==69.5.1`
- Fixed: MLflow DB version mismatch → matched container to Codespace version (`mlflow==3.11.1`)
- Fixed: sklearn version mismatch (`1.8.0` vs `1.5.0`) — warnings only, not breaking
- Fixed: `mlruns/` not mounted → added second volume mount
- Written: Helm chart (`infra/helm/geosentinel/`) — Deployment, Service, PVC templates

**Phase 4 — Monitoring:**
- Written: `drift_detector.py` — Evidently AI drift reports with HTML + JSON output
- Written: `metrics.py` — Prometheus counters, histograms, gauges
- Updated `app.py` — `/metrics` endpoint, `/drift/check` API endpoint
- Written: `docker-compose.yml` — API + Prometheus + Grafana full stack
- Fixed: data volume mount path (`/workspaces/...` → `/app/data`)
- Fixed: `docker-compose.yml` version attribute obsolete → removed

**Drift check result:**
```json
{
  "drift_score": 0.1429,
  "is_drifted": false,
  "drifted_features": ["ndvi_max"],
  "n_reference": 13,
  "n_current": 6
}
```

**Auto-retraining DAG:**
- Written: `retrain_pipeline.py` — BranchPythonOperator with drift threshold
- Flow: `check_drift → [drift≥0.3] → download_new_data → retrain → promote_model`
- Flow: `check_drift → [drift<0.3] → no_retraining_needed`
- Schedule: weekly on Mondays @ 08:00 UTC
- Test run: correctly branched to `no_retraining_needed` (score 0.1429 < threshold 0.3)

**Metrics confirmed working:**
```
geosentinel_predictions_total{result="normal"} 10.0
geosentinel_prediction_latency_seconds_count 10.0
geosentinel_model_version 2.0
geosentinel_drift_score 0.1429
```

**Key learnings:**
- Docker volume mounts must match exactly the path the application resolves — use `docker exec` to debug
- COG overview levels are the correct pattern for memory-efficient satellite data statistics
- Evidently `DataDriftPreset` requires minimum 4 samples in both reference and current sets
- MLflow model artifacts path (`mlruns/`) must be mounted separately from the tracking DB (`mlflow/`)
- `BranchPythonOperator` is the right Airflow pattern for conditional pipeline branching

**Files committed:**
```
src/serving/app.py          src/monitoring/drift_detector.py
src/monitoring/metrics.py   airflow/dags/retrain_pipeline.py
docker-compose.yml          Dockerfile
requirements-serving.txt    infra/helm/geosentinel/
infra/prometheus/           infra/grafana/
```

**Commit:** `feat: project complete - auto-retraining DAG, drift detection, full MLOps stack`

---

## Roadmap

| Phase | Goal | Status |
|---|---|---|
| 1 — Data Foundation | Automated, versioned data pipeline | Complete |
| 2 — Model Training | Reproducible experiments with MLflow | Complete |
| 3 — K8s Deployment | Model served as REST API on Kubernetes | Complete |
| 4 — Monitoring | Drift detection + automated retraining | Complete |
| 5 — Portfolio Polish | Docs, demo video, blog post | In Progress |

---

## Model Performance

| Run | Scenes | Anomalies | Mean Score | Status |
|---|---|---|---|---|
| `4a9f90fd` | 1 | 0 (0%) | 0.000 | Archived |
| `555c4341` | 19 | 1 (5.3%) | 0.044 | **Staging** |

**Flagged scene:** `S2A_32UMA_20240605_0_L2A` — June 5, 2024 (anomaly score: -0.0062)

---

## Getting Started

### Prerequisites
- Python 3.12+
- Docker
- GitHub Codespaces or local environment

### Quick Start

```bash
# 1. Clone
git clone https://github.com/riyabhattacharjee123/geosentinel-mlops.git
cd geosentinel-mlops

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download 20 Sentinel-2 scenes (no credentials needed)
python src/ingestion/bulk_download.py \
  --year 2024 --months 5 6 7 8 9 --scenes-per-month 4

# 4. Train the anomaly detection model
python src/training/train.py

# 5. Promote model to Staging
python src/training/promote_model.py --version 2 --stage Staging

# 6. Start the full stack (API + Prometheus + Grafana)
docker compose up

# 7. Test the API
curl http://localhost:8000/health
curl http://localhost:8000/docs      # Swagger UI

# 8. Run drift detection
curl -X POST http://localhost:8000/drift/check

# 9. View dashboards
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000  (admin / geosentinel)
```

### Run the Airflow pipelines

```bash
export AIRFLOW_HOME=/workspaces/geosentinel-mlops/airflow
export AIRFLOW__CORE__DAGS_FOLDER=/workspaces/geosentinel-mlops/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow db migrate

# Daily data pipeline
airflow dags test sentinel2_ndvi_pipeline $(date +%Y-%m-%d)

# Weekly auto-retraining check
airflow dags test geosentinel_auto_retrain $(date +%Y-%m-%d)
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/model/info` | GET | Current model version + metadata |
| `/predict` | POST | Single scene anomaly detection |
| `/predict/batch` | POST | Multiple scenes at once |
| `/metrics` | GET | Prometheus metrics |
| `/drift/check` | POST | Run Evidently drift report |
| `/docs` | GET | Interactive Swagger UI |

**Example prediction:**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "scene": "S2A_32UMA_20240605_0_L2A",
    "ndvi_mean": 0.027, "ndvi_std": 0.049,
    "ndvi_min": -0.250, "ndvi_max": 0.812,
    "vegetation_pct": 0.62, "water_pct": 8.15,
    "bare_soil_pct": 87.25
  }'
```

```json
{
  "scene": "S2A_32UMA_20240605_0_L2A",
  "prediction": "anomaly",
  "anomaly_score": -0.0062,
  "is_anomaly": true,
  "model_version": "2",
  "model_stage": "Staging"
}
```

---

## Resources

- [AWS Open Data — Sentinel-2 COGs](https://registry.opendata.aws/sentinel-2-l2a-cogs/)
- [Copernicus Data Space Documentation](https://documentation.dataspace.copernicus.eu/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently AI Documentation](https://docs.evidentlyai.com/)
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [DVC Documentation](https://dvc.org/doc)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Author

**Riya** — DevOps/Platform Engineer
 Frankfurt/Darmstadt, Germany

---
