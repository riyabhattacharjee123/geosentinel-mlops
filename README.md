# geosentinel-mlops
Description: End-to-end MLOps platform for Sentinel-2 vegetation anomaly detection

# 🛰️ GeoSentinel-MLOps

> An end-to-end MLOps platform for Earth Observation — detecting vegetation anomalies using Sentinel-2 satellite data, deployed on Kubernetes with full model versioning, serving, and drift monitoring.

[![Project Status](https://img.shields.io/badge/status-in%20progress-yellow)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![Phase](https://img.shields.io/badge/phase-1%20of%205-blue)](https://github.com/riyabhattacharjee123/geosentinel-mlops)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)

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
| Data Source | Copernicus Data Space Ecosystem (Sentinel-2 L2A) |
| Data Versioning | DVC |
| Experiment Tracking | MLflow |
| Model Registry | MLflow Model Registry |
| Pipeline Orchestration | Apache Airflow |
| Model Serving | FastAPI + Docker |
| Infrastructure | Kubernetes (kind → Oracle Cloud free tier) |
| IaC | Terraform |
| CI/CD | GitLab / GitHub Actions |
| Drift Monitoring | Evidently AI |
| Observability | Grafana + Prometheus |
| Language | Python 3.11 |

---

## 🗂️ Repository Structure

```
geosentinel-mlops/
├── src/
│   ├── ingestion/          # Data pipeline: auth, search, download
│   │   ├── auth.py         # OAuth2 token generation (CDSE)
│   │   ├── search.py       # OData catalog search with filters
│   │   └── download.py     # Streaming download with progress bar
│   ├── training/           # Model training & experiment tracking
│   ├── serving/            # FastAPI model serving endpoint
│   └── monitoring/         # Drift detection & alerting
├── airflow/
│   └── dags/               # Scheduled pipeline DAGs
├── data/
│   ├── raw/                # Downloaded Sentinel-2 .zip files
│   ├── processed/          # NDVI-computed NumPy/Parquet outputs
│   └── versioned/          # DVC-tracked dataset versions
├── infra/
│   ├── helm/               # Kubernetes Helm charts
│   └── terraform/          # Infrastructure as Code
├── models/                 # Saved model artifacts
├── notebooks/              # Exploratory analysis
├── tests/                  # Unit + integration tests
├── docs/                   # Architecture diagrams, decisions
├── .env.example            # Credential template (never commit .env)
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
- Generated S3 credentials (access key + secret key) from the CDSE S3 key manager
  - 12 TB/month free quota at 20 MBps
  - Endpoint: `https://eodata.dataspace.copernicus.eu`
- Understood two authentication methods:
  - **OAuth2 Bearer token** — for OData catalog search and single-product download
  - **S3 keys** — for bulk/high-performance data access via AWS-compatible protocol
- Token is fetched at runtime via POST to `https://identity.dataspace.copernicus.eu/...` — expires in ~600 seconds, never hardcoded

**4. Repository Setup**
- Created `geosentinel-mlops` GitHub repository (public, MIT license)
- Launched GitHub Codespace for cloud-based development
- Set up full project folder structure
- Fixed branch naming issue: local branch was `Main` → renamed to `main` to match GitHub remote using `git branch -m Main main`

**5. Code Written — Ingestion Module (Phase 1)**

Three modules written and tested:

`src/ingestion/auth.py`
- Fetches OAuth2 Bearer token from Copernicus identity server
- Reads credentials from `.env` via `python-dotenv`
- Raises on HTTP errors for clean failure handling

`src/ingestion/search.py`
- Queries the CDSE OData catalog API
- Filters by: geographic point (lon/lat), date range, cloud cover percentage
- Returns structured list of product metadata dicts
- Pretty-print helper for terminal output
- Tested: searched for Sentinel-2 L2A tiles over Frankfurt (8.68°E, 50.11°N), June 2024, <20% cloud → returned 5 products

`src/ingestion/download.py`
- Downloads a Sentinel-2 product by its OData UUID
- Streaming download with `tqdm` progress bar
- Skip-if-exists logic to avoid re-downloading
- Saves to `data/raw/` directory

**6. Key Learnings Today**
- CDSE replaced the old Copernicus Open Access Hub (SciHub) — all new projects should use `dataspace.copernicus.eu`
- The `$filter` syntax in OData uses `OData.CSC.Intersects` for spatial queries — different from standard OData
- Cloud cover filtering requires the nested `Attributes/OData.CSC.DoubleAttribute/any(...)` pattern
- S3 credentials on CDSE are separate from the OAuth2 token — two different auth systems for two different use cases
- Always use `git branch -m` not `git branch -M` when you want a safe rename that checks for conflicts

**Files committed:**
```
src/ingestion/auth.py
src/ingestion/search.py
src/ingestion/download.py
src/ingestion/__init__.py
data/raw/.gitkeep
data/processed/.gitkeep
data/versioned/.gitkeep
.env.example
requirements.txt
```

**Commit:** `feat: Phase 1 - Sentinel-2 ingestion pipeline (auth, search, download)`

---

**⏭️ Next Session (Day 2 — Phase 1 continued):**
- Wire `search.py` + `download.py` into an **Airflow DAG** that runs on a schedule
- Add **DVC** for dataset versioning
- Download a real Sentinel-2 tile and verify the `.zip` contents
- Milestone: Airflow DAG runs, new satellite data lands versioned in DVC

---

## 🗺️ 16-Week Roadmap

| Phase | Weeks | Goal | Status |
|---|---|---|---|
| 1 — Data Foundation | 1–3 | Automated, versioned data pipeline | 🟡 In Progress |
| 2 — Model Training | 4–6 | Reproducible experiments with MLflow | ⬜ Not Started |
| 3 — K8s Deployment | 7–9 | Model served as REST API on Kubernetes | ⬜ Not Started |
| 4 — Monitoring | 10–12 | Drift detection + automated retraining | ⬜ Not Started |
| 5 — Portfolio Polish | 13–16 | Docs, demo video, blog post | ⬜ Not Started |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- GitHub Codespaces or local Docker
- Copernicus Data Space account → [dataspace.copernicus.eu](https://dataspace.copernicus.eu)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/riyabhattacharjee123/geosentinel-mlops.git
cd geosentinel-mlops

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up credentials
cp .env.example .env
# Edit .env with your Copernicus Data Space credentials

# 4. Test the connection
cd src/ingestion
python auth.py
```

---

## 📚 Resources

- [Copernicus Data Space Documentation](https://documentation.dataspace.copernicus.eu/)
- [CDSE OData API Reference](https://documentation.dataspace.copernicus.eu/APIs/OData.html)
- [CDSE S3 Access Guide](https://documentation.dataspace.copernicus.eu/APIs/S3.html)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently AI Documentation](https://docs.evidentlyai.com/)

---

## 👤 Author

**Ree** — DevOps/Platform Engineer @ ESA  
Transitioning into MLOps/AI Infrastructure Engineering by December 2026  
📍 Frankfurt/Darmstadt, Germany

---





License: MIT
