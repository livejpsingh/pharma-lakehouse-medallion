# Deployment & Operations Guide

Step-by-step instructions for running the Medallion Lakehouse pipeline locally, inside Docker Desktop, and deploying to cloud production environments.

---

## 1. Quick Start with Docker Desktop (Recommended)

Docker Compose provides the most reproducible, zero-configuration local execution environment.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows or macOS) running.
- Ensure Docker Compose V2 is enabled.

### Run with a Single Command
```bash
# Build runner container and execute the entire pipeline end-to-end
docker compose up --build
```

### What Happens Automatically:
1. Starts the `minilake` emulator on port `8000` with volume mounts to `./data` and `./exports`.
2. Waits for MiniLake health check (`http://localhost:8000/_minilake/health`) to return `ok`.
3. Runs the `pipeline` container (OpenJDK 21 + Python 3.11).
4. Executes `scripts/run_all.py` (Catalog &rarr; Bronze Ingestion &rarr; Silver Cleanse &rarr; Gold Metrics &rarr; CSV Export).
5. Output CSVs appear in `./exports/`.

---

## 2. Local Native Execution (Without Docker)

For developers who prefer running scripts directly on their host machine:

### Prerequisites
- Python 3.11 or Python 3.12.
- Java 8, 11, 17, or 21 (required by PySpark).
- [MiniLake Docker container](https://github.com/dmux/minilake) running on port `8000`.

### Step 1: Start MiniLake Container
```bash
docker run -d \
  --name minilake \
  -p 8000:8000 \
  -v "${PWD}/data:/data" \
  -v "${PWD}/exports:/data/exports" \
  ghcr.io/dmux/minilake:latest
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Master Pipeline
```bash
python scripts/run_all.py
```

### Or Run Individual Medallion Stages:
```bash
# 1. Setup Catalog and Medallion Schemas
python scripts/01_setup_catalog.py

# 2. Ingest Raw CSV to Bronze Delta Lake
python scripts/02_bronze_ingest.py

# 3. Cleanse & Evaluate Data Quality into Silver
python scripts/03_silver_transform.py

# 4. Generate Gold Aggregations & Export CSVs
python scripts/04_gold_metrics.py
```

---

## 3. Environment Variables Reference

The pipeline config reads from environment variables with fallback defaults:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MINILAKE_HOST` | `http://localhost:8000` | MiniLake endpoint (or `http://minilake:8000` in Docker). |
| `MINILAKE_TOKEN` | `dev` | Databricks SDK bearer token (MiniLake accepts any token). |
| `DATA_DIR` | `<PROJECT_ROOT>/data` | Directory where raw data and Delta tables reside. |
| `EXPORTS_DIR` | `<PROJECT_ROOT>/exports` | Directory where exported Gold CSVs are saved. |
| `CONTAINER_DATA_ROOT` | `/data` | Volume mount path inside the MiniLake container. |
| `DEFAULT_WAREHOUSE_NAME` | `local-duckdb-warehouse` | MiniLake SQL warehouse name. |

---

## 4. Production Cloud Migration (Databricks AWS / Azure / GCP)

To promote this pipeline to an enterprise cloud Databricks workspace:

1. **Unity Catalog Storage**:
   - Change `DELTA_BRONZE_PATH` in `scripts/config.py` from local `/data/...` to your cloud object storage:
     - AWS S3: `s3://<my-company-lakehouse>/pharmacy/bronze/sales_raw`
     - Azure ADLS Gen2: `abfss://lakehouse@<storage-account>.dfs.core.windows.net/pharmacy/bronze/`
     - GCP GCS: `gs://<my-company-lakehouse>/pharmacy/bronze/`

2. **Authentication**:
   - Set standard Databricks authentication environment variables:
     ```bash
     export DATABRICKS_HOST="https://adb-<workspace-id>.azuredatabricks.net"
     export DATABRICKS_TOKEN="dapi..."
     ```

3. **Compute Engine**:
   - On cloud Databricks, SQL queries in `03_silver_transform.py` and `04_gold_metrics.py` execute on Databricks Serverless SQL Warehouses or Photon-accelerated clusters with standard Spark SQL compatibility.

4. **Orchestration**:
   - Package the repository as a **Databricks Asset Bundle (DAB)** or trigger via **Apache Airflow** using the `DatabricksSubmitRunOperator`.
