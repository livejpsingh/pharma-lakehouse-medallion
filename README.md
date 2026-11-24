# Pharmacy Sales & Inventory Risk Analysis (Local Medallion Architecture)

A production-grade, reproducible data engineering capstone project demonstrating the **Medallion (Bronze/Silver/Gold) Architecture** locally without any cloud account or cost, powered by **MiniLake** (local Databricks API emulator) and **Power BI Desktop**.

---

## 1. Project Architecture

- **Bronze Layer (`pharmacy.bronze.sales_raw`)**: Raw CSV ingested via PySpark with `inferSchema=False` (untyped strings), written idempotently as Delta Lake tables, and registered as `EXTERNAL DELTA` in MiniLake Unity Catalog.
- **Silver Layer (`pharmacy.silver.sales_clean`)**: Cleaned, typed, and validated via DuckDB SQL using the Databricks SDK Statement Execution API. Filtered for positive revenue and valid sales dates.
- **Data Quality Table (`pharmacy.silver.dq_report`)**: Tracks raw vs cleansed row counts, rejected records, and pass percentages.
- **Gold Layer (`pharmacy.gold.*`)**:
  - `daily_sales`: Daily regional revenue and units trend.
  - `drug_performance`: Revenue, units sold, and revenue ranking (`RANK() OVER`).
  - `rep_performance`: Sales representative volume, revenue, and average order value.
- **Reporting Layer**: DuckDB `COPY` exports Gold tables as CSVs into `./exports/`, visualized via Power BI Desktop.

---

## 2. Directory Structure

```
databrick-poc1/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/
│   │   └── pharma_sales.csv
│   └── delta/                      # Container mounted volume
├── exports/                        # Exported Gold CSVs for Power BI
│   ├── daily_sales.csv
│   ├── drug_performance.csv
│   └── rep_performance.csv
├── dashboard/
│   └── pharmacy_sales_analytics.pbix
├── docs/
│   └── architecture.md
└── scripts/
    ├── config.py
    ├── 01_setup_catalog.py
    ├── 02_bronze_ingest.py
    ├── 03_silver_transform.py
    └── 04_gold_metrics.py
```

---

## 3. Environment & MiniLake Setup

### Step 1: Start MiniLake Container
Run MiniLake with a volume mount mapping the host `./data` and `./exports` folder to `/data` inside the container:

```bash
docker run -d \
  --name minilake \
  -p 8000:8000 \
  -v "${PWD}/data:/data" \
  -v "${PWD}/exports:/data/exports" \
  ghcr.io/dmux/minilake:latest
```

### Step 2: Health Check
Verify MiniLake is healthy and ready to accept SDK calls:
```bash
curl -s http://localhost:8000/_minilake/health
```
Expected response: `{"status":"ok"}`

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 4. Pipeline Execution Options

### Option A: Docker Compose (Recommended for Local Testing)
Execute the entire pipeline and MiniLake emulator with a single command via Docker Desktop:

```bash
# Build and run the entire pipeline end-to-end
docker compose up --build
```

### Option B: Step-by-Step Execution
Execute each script sequentially:

```bash
# All-in-one execution:
python scripts/run_all.py

# Or run individual stages:
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

## 5. MiniLake Constraints & Design Rules

| Feature | Supported in MiniLake? | Project Design Decision |
| :--- | :--- | :--- |
| **Databricks SDK** | Yes (Core APIs) | Connect via `WorkspaceClient(host="http://localhost:8000", token="dev")` |
| **SQL Engine** | DuckDB (NOT Spark SQL) | Use DuckDB dialect (`TRY_CAST`, `strftime`, standard ANSI windows) |
| **Managed Tables** | DuckDB internal only | **Never use MANAGED for Spark tables**. Use `EXTERNAL DELTA` under `/data/` |
| **In-place Delta UPDATE** | Limited in DuckDB | Use idempotent `CREATE TABLE AS SELECT (CTAS)` |
| **DLT / Expectations** | No | Replaced with explicit `pharmacy.silver.dq_report` table |
| **MLflow / Lakeview** | No | Replaced with Power BI Desktop local reporting |

---

## 6. Power BI Desktop Walkthrough

1. Open **Power BI Desktop** (Free).
2. Click **Get Data** -> **Text/CSV**.
3. Load the 3 generated files from `exports/`:
   - `daily_sales.csv`
   - `drug_performance.csv`
   - `rep_performance.csv`
4. Create the 4 core visuals:
   - **Card Visual 1**: Total Revenue (`SUM(daily_sales[total_revenue])`).
   - **Card Visual 2**: Top Drug by Revenue (`drug_performance` filtered by `revenue_rank = 1`).
   - **Line Chart**: `sale_date` (X-axis) vs `total_revenue` (Y-axis), broken down by `region` (Legend).
   - **Table Visual**: `sales_representative`, `total_revenue`, `avg_order_value`, `order_count`.
5. Save the report to `dashboard/pharmacy_sales_analytics.pbix`.
