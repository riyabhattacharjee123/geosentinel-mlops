# 🛰️ GeoSentinel-MLOps

> An end-to-end MLOps platform for Earth Observation — detecting vegetation anomalies using Sentinel-2 satellite data, deployed on Kubernetes with full model versioning, serving, and drift monitoring.

[![Project Status](https://img.shields.io/badge/status-in%20progress-yellow)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![Phase](https://img.shields.io/badge/phase-3%20of%205-blue)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)

---

## 🎯 Project Goal

Build a production-grade MLOps platform that:
- Ingests free Copernicus Sentinel-2 satellite imagery on a schedule
- Computes NDVI (vegetation index) and detects anomalies using ML
- Deploys the model as a REST API on Kubernetes
- Monitors model drift with automated retraining triggers
- Demonstrates the full MLOps lifecycle end-to-end for portfolio purposes

**Why this project?** This project bridges DevOps/Platform Engineering with ML — leveraging real Earth Observation domain expertise (ESA/Copernicus) to build something rare: infrastructure-focused ML tooling for satellite data pipelines.

---

## 🧱 Tech Stack

| Layer | Tool |
|---|---|
| Data Source | AWS Open Data Registry (Sentinel-2 L2A COGs) |
| Data Versioning | DVC |
| Experiment Tracking | MLflow |
| Model Registry | MLflow Model Registry |
| Pipeline Orchestration | Apache Airflow 2.10.4 |
| Model Serving | FastAPI + Docker |
| Infrastructure | Kubernetes (kind → Oracle Cloud free tier) |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Drift Monitoring | Evidently AI |
| Observability | Grafana + Prometheus |
| Language | Python 3.12 |

---

## 🗂️ Repository Structure

```
geosentinel-mlops/
├── src/
│   ├── ingestion/
│   │   ├── auth.py             # OAuth2 token generation (CDSE)
│   │   ├── search.py           # OData catalog search with filters
│   │   ├── download_aws.py     # Band downloader via AWS Open Data (no auth)
│   │   ├── compute_ndvi.py     # NDVI computation from B04/B08 bands (COG overview)
│   │   └── bulk_download.py    # Parameterised bulk scene downloader
│   ├── training/
│   │   ├── features.py         # Feature extraction from NDVI stats JSON
│   │   ├── train.py            # Isolation Forest + MLflow experiment tracking
│   │   └── promote_model.py    # Promote model version to Staging/Production
│   ├── serving/                # FastAPI model serving endpoint (Phase 3)
│   └── monitoring/             # Drift detection & alerting (Phase 4)
├── airflow/
│   └── dags/
│       └── sentinel2_pipeline.py  # Scheduled NDVI pipeline DAG
├── data/
│   ├── raw/                    # Downloaded GeoTIFF bands (DVC-tracked)
│   ├── processed/              # NDVI stats JSON files (19 scenes)
│   └── versioned/              # DVC metadata
├── mlflow/                     # MLflow tracking DB + artifacts
├── models/                     # Scene predictions + feature stats JSON
├── infra/
│   ├── helm/                   # Kubernetes Helm charts (Phase 3)
│   └── terraform/              # Infrastructure as Code (Phase 3)
├── notebooks/                  # Exploratory analysis
├── tests/                      # Unit + integration tests
├── docs/                       # Architecture diagrams, decisions
├── .env.example                # Credential template (never commit .env)
└── requirements.txt
```

---

## 🗓️ Development Journal

### ✅ Day 1 — April 22, 2026

**Session Goal:** Research, planning, and project bootstrap.

**What I did:**

**1. Research & Direction Setting**
- Investigated current state of AI/ML impact on DevOps and Platform Engineering roles
- Key finding: AI is not replacing DevOps — it is reshaping it toward higher-level roles. The real opportunity is **MLOps** — bridging infrastructure expertise with ML system deployment
- Decided on transition path: DevOps/Platform Engineer → MLOps / AI Infrastructure Engineer

**2. Project Design**
- Designed the GeoSentinel-MLOps project: end-to-end MLOps pipeline for Sentinel-2 vegetation anomaly detection
- Chose NDVI anomaly detection: familiar data format, natural concept drift, simple model, real-world story

**3. Credentials & API Setup**
- Created Copernicus Data Space Ecosystem account
- Generated S3 credentials (12 TB/month free quota)
- Understood two auth methods: OAuth2 Bearer token and S3 keys

**4. Repository Setup**
- Created `geosentinel-mlops` GitHub repository (public, MIT license)
- Launched GitHub Codespace, set up folder structure
- Fixed branch naming: `Main` → `main`

**5. Code Written**

`src/ingestion/auth.py` — OAuth2 token generation  
`src/ingestion/search.py` — OData catalog search  
`src/ingestion/download.py` — Streaming product download

**Key Learnings:** CDSE replaced SciHub. OData spatial queries use `OData.CSC.Intersects`. Cloud cover filter requires nested `Attributes/OData.CSC.DoubleAttribute/any(...)`.

**Commit:** `feat: Phase 1 - Sentinel-2 ingestion pipeline (auth, search, download)`

---

### ✅ Day 2 — May 4, 2026

**Session Goal:** Complete Phase 1 — working, scheduled, versioned satellite data pipeline.

**What I did:**

**1. Debugging CDSE API Access**
- Hit 403 Forbidden on both OData API and `sentinelsat` library
- Root cause: `sentinelsat` uses deprecated SciHub/OpenSearch endpoint
- Decision: switched to **AWS Open Data Registry** — Sentinel-2 L2A on `sentinel-cogs` bucket, no auth needed

**2. AWS Open Data Downloader**

`src/ingestion/download_aws.py` — lists and downloads B04+B08 bands via anonymous S3. ~20MB per scene vs 800MB full zip.

**3. NDVI Computation**

`src/ingestion/compute_ndvi.py` — computes NDVI, saves GeoTIFF + stats JSON.

First result (Frankfurt, June 2, 2024):
```
Mean NDVI  : 0.0276  |  Vegetation: 0.6%  |  Bare soil: 87.3%
```
Expected for early June before crops develop.

**4. Airflow DAG**

`airflow/dags/sentinel2_pipeline.py` — three tasks: `download_bands → compute_ndvi → version_data`. Scheduled daily at 06:00 UTC. All 3 tasks green on first test run.

**5. Infrastructure Fixes**
- Airflow `db init` deprecated → switched to `airflow db migrate`
- Fixed `typing_extensions` / `pydantic-core` conflict
- Fixed `fsspec` / DVC conflict
- Switched Claude Code from free to paid account in Codespace

**Key Learnings:** Airflow 2.10.4 = first version with full Python 3.12 support. XCom passes data between tasks via `ti.xcom_push()` / `ti.xcom_pull()`.

**Commit:** `feat: Phase 1 complete - Airflow DAG for Sentinel-2 NDVI pipeline`

---

### ✅ Day 3 — May 5, 2026

**Session Goal:** Complete Phase 2 — MLflow experiment tracking, anomaly detection model trained and registered.

**What I did:**

**1. Feature Extraction**

Written: `src/training/features.py`
- Converts NDVI stats JSON → 7-feature numpy vector
- Features: `ndvi_mean`, `ndvi_std`, `ndvi_min`, `ndvi_max`, `vegetation_pct`, `water_pct`, `bare_soil_pct`
- `load_all_features()` loads all JSON files in `data/processed/` into a feature matrix

**2. First Training Run (1 scene)**
- Trained Isolation Forest on 1 scene — score was 0.0 (expected, can't detect anomalies with 1 data point)
- MLflow run `4a9f90fd` created, model registered as **Version 1**

**3. Memory Issue + Fix**
- Bulk downloading 20 full-resolution scenes terminated the Codespace (146MB per band × 2 = 460MB per scene)
- Fix: updated `compute_ndvi.py` to read at 1/10 resolution using **COG overview levels**
- `rasterio` `out_shape` parameter reads a downsampled version — ~5MB per scene, same statistical accuracy

**4. Bulk Download**

Written: `src/ingestion/bulk_download.py`
- Fully parameterised: `--year`, `--months`, `--scenes-per-month`, `--utm-zone`, `--lat-band`, `--square`
- Skip-if-exists logic, progress summary, error handling per scene
- Downloaded 20 scenes: May–September 2024, 4 per month, tile 32/U/MA (Frankfurt)

```bash
python src/ingestion/bulk_download.py \
  --year 2024 --months 5 6 7 8 9 --scenes-per-month 4
```

Result: 18 completed, 2 skipped (already existed), 0 failed.

**5. Second Training Run (19 scenes)**

MLflow run `555c4341` — trained on 19 scenes:

```
Scenes trained on : 19
Normal scenes     : 18
Anomalies flagged : 1  (5.3%)
Mean score        : 0.044396

🚨 S2A_32UMA_20240605_0_L2A: score=-0.0062  ← anomaly
✅ 18 other scenes: scores 0.0007 to 0.1131
```

The June 5 scene was flagged as anomalous — its NDVI feature vector was the most isolated point in the 7-dimensional feature space.

**6. MLflow Model Registry**

```
Version 1  →  Archived    (1 scene, outdated)
Version 2  →  Staging     (19 scenes, current candidate)
```

Written: `src/training/promote_model.py`
- Parameterised: `--version`, `--stage`
- Shows before/after version table with stage icons
- Promotes with `archive_existing_versions=True`

**7. MLflow UI**
- Launched at `localhost:5000` via Codespace port forwarding
- Experiment `geosentinel-ndvi-anomaly` visible with both runs
- Model registry shows Version 1 (Archived) and Version 2 (Staging)

**Key Learnings:**
- COG overview levels are the correct approach for memory-efficient satellite data processing — always downsample for statistics, only use full resolution for visual output
- Isolation Forest `contamination` parameter = expected anomaly fraction — set to 0.05 (5%) based on domain knowledge
- MLflow `transition_model_version_stage` is deprecated in 2.9.0+ — will migrate to aliases (`@champion`, `@challenger`) in Phase 4
- Negative anomaly score = most isolated point in feature space = genuine outlier
- 1 scene is not enough to train any anomaly model — minimum ~10 needed for meaningful results

**Files committed:**
```
src/training/features.py
src/training/train.py
src/training/promote_model.py
src/ingestion/bulk_download.py
src/ingestion/compute_ndvi.py  (updated: COG overview reading)
mlflow/mlflow.db
models/scene_predictions.json
models/feature_stats.json
```

**Commit:** `feat: Phase 2 complete - MLflow tracking, 19-scene anomaly model v2 in Staging`

---

**⏭️ Next Session (Day 4 — Phase 3 begins):**
- Write `src/serving/app.py` — FastAPI endpoint wrapping the Production model
- `POST /predict` accepts NDVI features, returns anomaly score + label
- Containerise with Docker
- Write Helm chart for Kubernetes deployment
- Deploy locally with `kind`

---

## 🗺️ 16-Week Roadmap

| Phase | Weeks | Goal | Status |
|---|---|---|---|
| 1 — Data Foundation | 1–3 | Automated, versioned data pipeline | ✅ Complete |
| 2 — Model Training | 4–6 | Reproducible experiments with MLflow | ✅ Complete |
| 3 — K8s Deployment | 7–9 | Model served as REST API on Kubernetes | 🟡 In Progress |
| 4 — Monitoring | 10–12 | Drift detection + automated retraining | ⬜ Not Started |
| 5 — Portfolio Polish | 13–16 | Docs, demo video, blog post | ⬜ Not Started |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- GitHub Codespaces or local Docker

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/riyabhattacharjee123/geosentinel-mlops.git
cd geosentinel-mlops

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download Sentinel-2 bands (no credentials needed)
python src/ingestion/bulk_download.py --year 2024 --months 5 6 7 8 9 --scenes-per-month 4

# 4. Train the anomaly detection model
python src/training/train.py

# 5. View experiments in MLflow UI
mlflow ui --backend-store-uri sqlite:////workspaces/geosentinel-mlops/mlflow/mlflow.db

# 6. Run the full pipeline via Airflow
export AIRFLOW_HOME=/workspaces/geosentinel-mlops/airflow
export AIRFLOW__CORE__DAGS_FOLDER=/workspaces/geosentinel-mlops/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow db migrate
airflow dags test sentinel2_ndvi_pipeline $(date +%Y-%m-%d)
```

---

## 📊 Model Performance

| Run | Scenes | Anomalies | Mean Score | Status |
|---|---|---|---|---|
| `4a9f90fd` | 1 | 0 | 0.000 | Archived |
| `555c4341` | 19 | 1 (5.3%) | 0.044 | **Staging** |

**Flagged scene:** `S2A_32UMA_20240605_0_L2A` — June 5, 2024 (score: -0.0062)

---

## 📚 Resources

- [AWS Open Data — Sentinel-2 COGs](https://registry.opendata.aws/sentinel-2-l2a-cogs/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently AI Documentation](https://docs.evidentlyai.com/)
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [DVC Documentation](https://dvc.org/doc)

---

## 👤 Author

**Ree** — DevOps/Platform Engineer @ ESA  
Transitioning into MLOps/AI Infrastructure Engineering by December 2026  
📍 Frankfurt/Darmstadt, Germany

---

*This project is part of a self-directed learning journey toward Platform/MLOps Engineering.*
