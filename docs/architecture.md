# Architecture & Engineering Design

## Medallion Architecture on MiniLake (Local Databricks API Emulator)

```mermaid
flowchart TD
    A["Raw CSV Source<br/>(Kaggle Sample Data)"] -->|Spark read inferSchema=False| B["Bronze Layer<br/>(Delta Lake on disk: /data/delta/...)"]
    B -->|SDK Register EXTERNAL DELTA| C["pharmacy.bronze.sales_raw<br/>(Unity Catalog Registration)"]
    C -->|DuckDB SQL CTAS<br/>Cast, Filter, Validate| D["pharmacy.silver.sales_clean<br/>+ silver.dq_report"]
    D -->|DuckDB Aggregations<br/>Window Functions| E["Gold Layer<br/>daily_sales<br/>drug_performance<br/>rep_performance"]
    E -->|DuckDB COPY TO CSV| F["Exported CSVs<br/>(/data/exports/*.csv)"]
    F -->|Local File Load| G["Power BI Desktop<br/>Interactive Dashboard"]
```

## Architectural Tenets & Rules

### 1. Dual-Engine Model: Spark vs DuckDB
MiniLake implements the Databricks Workspace & Unity Catalog APIs locally. However, its compute engine is **DuckDB**, not Spark SQL.

- **Bronze writes**: Spark writes Delta files to `/data/delta/...` with ACID transactional guarantees.
- **Table Registration**: Tables written by Spark must be registered as `EXTERNAL` with `format=DELTA` pointing to `/data/...`.
- **Managed Table Trap**: MiniLake `MANAGED` tables are internal DuckDB tables. If created as `MANAGED`, Spark cannot see or read them.
- **Transformations & Gold**: Handled directly through the Databricks Statement Execution API executing DuckDB SQL.

### 2. DuckDB Delta Operations Strategy
DuckDB's Delta extension provides fast read and CTAS capability, but limited support for in-place atomic row updates (`UPDATE` / `DELETE`). Consequently, the Silver and Gold transformations follow the idempotent **CTAS (Create Table As Select)** pattern with explicit table recreation.

### 3. Data Quality & Observability
Because MiniLake does not support Databricks Lakehouse Expectations or Delta Live Tables (DLT), the pipeline computes and persists a dedicated data quality tracking table (`pharmacy.silver.dq_report`) logging:
- Ingested Bronze record count
- Validated Silver record count
- Dropped record count (invalid dates, negative units/revenue)
- DQ pass percentage and timestamp
