# 🛰️ GeoSentinel-MLOps

> An end-to-end MLOps platform for Earth Observation — detecting vegetation anomalies using Sentinel-2 satellite data, deployed on Kubernetes with full model versioning, serving, and drift monitoring.

[![Project Status](https://img.shields.io/badge/status-in%20progress-yellow)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![Phase](https://img.shields.io/badge/phase-2%20of%205-blue)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
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
│   │   └── compute_ndvi.py     # NDVI computation from B04/B08 bands
│   ├── training/               # Model training & experiment tracking (Phase 2)
│   ├── serving/                # FastAPI model serving endpoint (Phase 3)
│   └── monitoring/             # Drift detection & alerting (Phase 4)
├── airflow/
│   └── dags/
│       └── sentinel2_pipeline.py  # Scheduled NDVI pipeline DAG
├── data/
│   ├── raw/                    # Downloaded GeoTIFF bands (DVC-tracked)
│   ├── processed/              # NDVI GeoTIFF + stats JSON (DVC-tracked)
│   └── versioned/              # DVC metadata
├── infra/
│   ├── helm/                   # Kubernetes Helm charts (Phase 3)
│   └── terraform/              # Infrastructure as Code (Phase 3)
├── models/                     # Saved model artifacts
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
- Read multiple sources (Pulumi, Medium, DevOps.com, KodeKloud, Interview Kickstart) on the topic
- Key finding: AI is not replacing DevOps — it is reshaping it toward higher-level roles. The real opportunity is **MLOps** — bridging infrastructure expertise with ML system deployment
- Decided on transition path: DevOps/Platform Engineer → MLOps / AI Infrastructure Engineer

**2. Project Design**
- Designed the GeoSentinel-MLOps project concept: an end-to-end MLOps pipeline for Sentinel-2 vegetation anomaly detection
- Chose NDVI anomaly detection because:
  - Familiar data format (GeoTIFF/NetCDF) from ESA background — no domain learning curve
  - Seasonal variation creates natural concept drift for realistic MLOps monitoring
  - Simple baseline model (Random Forest) keeps focus on infrastructure, not ML research
  - Real-world story (drought, crop stress, wildfire risk) is compelling in interviews
- Mapped the full 16-week, 5-phase roadmap

**3. Credentials & API Setup**
- Created Copernicus Data Space Ecosystem account at `dataspace.copernicus.eu`
- Generated S3 credentials from the CDSE S3 key manager (12 TB/month free quota)
- Understood two authentication methods: OAuth2 Bearer token (OData API) and S3 keys (bulk access)

**4. Repository Setup**
- Created `geosentinel-mlops` GitHub repository (public, MIT license)
- Launched GitHub Codespace for cloud-based development
- Set up full project folder structure
- Fixed branch naming issue: `Main` → `main` using `git branch -m Main main`

**5. Code Written**

`src/ingestion/auth.py` — OAuth2 token generation from Copernicus identity server  
`src/ingestion/search.py` — OData catalog search filtered by location, date, cloud cover  
`src/ingestion/download.py` — Streaming product download with tqdm progress bar

**6. Key Learnings**
- CDSE replaced the old SciHub — all new projects use `dataspace.copernicus.eu`
- OData spatial queries use `OData.CSC.Intersects` — different from standard OData
- Cloud cover filtering requires nested `Attributes/OData.CSC.DoubleAttribute/any(...)` pattern

**Commit:** `feat: Phase 1 - Sentinel-2 ingestion pipeline (auth, search, download)`

---

### ✅ Day 2 — May 4, 2026

**Session Goal:** Complete Phase 1 — working, scheduled, versioned satellite data pipeline.

**What I did:**

**1. Debugging CDSE API Access**
- Hit 403 Forbidden errors on both the OData API and `sentinelsat` library
- Root cause: `sentinelsat` uses the deprecated SciHub/OpenSearch endpoint which CDSE no longer supports
- The `contains()` OData filter was also unsupported, returning 0 results
- Decision: switched data source to **AWS Open Data Registry** — Sentinel-2 L2A is mirrored on S3 bucket `sentinel-cogs`, completely free, no authentication required

**2. AWS Open Data Downloader**

Written: `src/ingestion/download_aws.py`
- Lists available scenes by UTM tile and month via anonymous S3 access
- Downloads only NDVI-relevant bands: **B04.tif** (Red) and **B08.tif** (NIR)
- ~20MB total vs 800MB for full product zip — faster, no wasted storage
- Skip-if-exists logic to avoid duplicate downloads
- Tested: listed 18 Sentinel-2 L2A scenes for tile 32UMA (Frankfurt), June 2024

**3. NDVI Computation**

Written: `src/ingestion/compute_ndvi.py`
- Reads B04 + B08 GeoTIFF bands using `rasterio`
- Computes `NDVI = (B08 - B04) / (B08 + B04)` with divide-by-zero protection
- Clips output to valid range `[-1.0, 1.0]`
- Saves NDVI as GeoTIFF + a companion JSON stats file
- First real result for Frankfurt (June 2, 2024):

```
Mean NDVI  : 0.0276
Vegetation : 0.6%   (NDVI > 0.3)
Water      : 8.2%   (NDVI < 0.0)
Bare soil  : 87.3%  (NDVI 0.0–0.1)
```

> Note: 87% bare soil is expected for early June before crops fully develop. July/August tiles will show 40–60% vegetation — that seasonal delta is what the anomaly model will learn.

**4. Airflow DAG**

Written: `airflow/dags/sentinel2_pipeline.py`
- Three-task pipeline: `download_bands → compute_ndvi → version_data`
- Scheduled daily at 06:00 UTC
- Uses XCom to pass `scene_dir` and `ndvi_path` between tasks
- Execution date drives which year/month is queried from AWS

**5. Infrastructure Fixes**
- Resolved Airflow `db init` deprecation — switched to `airflow db migrate`
- Fixed `typing_extensions` / `pydantic-core` import conflict by upgrading packages
- Fixed `fsspec` / DVC conflict: `pip install "fsspec>=2023.1.0" "dvc>=3.0.0"`
- Switched Claude Code from free account to paid subscription in Codespace

**6. DAG Test Run — All 3 Tasks Green ✅**
```
[SUCCESS] download_bands  — 18 scenes found, B04+B08 ready
[SUCCESS] compute_ndvi    — NDVI GeoTIFF + stats JSON generated (10980×10980px)
[SUCCESS] version_data    — DVC tracking updated, git commit issued
```

**7. Key Learnings**
- Sentinel-2 L2A COGs on AWS (`sentinel-cogs` bucket) require zero auth — easiest EO data access
- UTM tile 32UMA = Frankfurt/Rhine-Main region
- NDVI values in early June are low due to crop growth cycle — not a data error
- Airflow XCom is how tasks pass data between each other — `ti.xcom_push()` / `ti.xcom_pull()`
- Airflow 2.10.4 is the first version with full Python 3.12 support

**Files committed:**
```
src/ingestion/download_aws.py
src/ingestion/compute_ndvi.py
airflow/dags/sentinel2_pipeline.py
data/processed/S2A_32UMA_20240602_0_L2A_NDVI.tif
data/processed/S2A_32UMA_20240602_0_L2A_NDVI_stats.json
```

**Commit:** `feat: Phase 1 complete - Airflow DAG for Sentinel-2 NDVI pipeline`

---

**⏭️ Next Session (Day 3 — Phase 2 begins):**
- Install and configure **MLflow**
- Build `src/training/train.py` — feature extraction from NDVI stats
- Train baseline **Isolation Forest** anomaly detection model
- Log all experiments (parameters, metrics, artifacts) to MLflow
- Register best model in MLflow Model Registry

---

## 🗺️ 16-Week Roadmap

| Phase | Weeks | Goal | Status |
|---|---|---|---|
| 1 — Data Foundation | 1–3 | Automated, versioned data pipeline | ✅ Complete |
| 2 — Model Training | 4–6 | Reproducible experiments with MLflow | 🟡 In Progress |
| 3 — K8s Deployment | 7–9 | Model served as REST API on Kubernetes | ⬜ Not Started |
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
python src/ingestion/download_aws.py

# 4. Compute NDVI
python src/ingestion/compute_ndvi.py

# 5. Run full pipeline via Airflow
export AIRFLOW_HOME=/workspaces/geosentinel-mlops/airflow
export AIRFLOW__CORE__DAGS_FOLDER=/workspaces/geosentinel-mlops/airflow/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow db migrate
airflow dags test sentinel2_ndvi_pipeline $(date +%Y-%m-%d)
```

---

## 📚 Resources

- [AWS Open Data — Sentinel-2 COGs](https://registry.opendata.aws/sentinel-2-l2a-cogs/)
- [Copernicus Data Space Documentation](https://documentation.dataspace.copernicus.eu/)
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

*This project is part of a structured 10-month self-directed learning journey toward Platform/MLOps Engineering.*
