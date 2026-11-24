"""
Script 03: Silver Transform & Data Quality Report
Executes DuckDB SQL via Databricks SDK Statement Execution API.
Transforms untyped bronze data into pharmacy.silver.sales_clean using CTAS.
Builds pharmacy.silver.dq_report to track row validation metrics.
"""

import logging
import sys
import time

from config import (
    DEFAULT_WAREHOUSE_NAME,
    MINILAKE_HOST,
    MINILAKE_TOKEN,
    TABLE_BRONZE_RAW,
    TABLE_SILVER_CLEAN,
    TABLE_SILVER_DQ,
)
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_or_create_sql_warehouse(w: WorkspaceClient) -> str:
    """Ensure a SQL warehouse exists on MiniLake and return its ID."""
    warehouses = list(w.warehouses.list())
    for wh in warehouses:
        if wh.name == DEFAULT_WAREHOUSE_NAME:
            logger.info("Found existing warehouse '%s' (ID: %s)", wh.name, wh.id)
            return wh.id

    logger.info("Creating warehouse '%s' on MiniLake...", DEFAULT_WAREHOUSE_NAME)
    created = w.warehouses.create(
        name=DEFAULT_WAREHOUSE_NAME,
        cluster_size="2X-Small",
        min_num_clusters=1,
        max_num_clusters=1,
        auto_stop_mins=0,
    )
    # Handle wait or direct id
    warehouse_id = created.id if hasattr(created, "id") and created.id else created.result().id
    logger.info("Created warehouse ID: %s", warehouse_id)
    return warehouse_id


def execute_sql(w: WorkspaceClient, warehouse_id: str, query: str, description: str = "") -> None:
    """Execute a DuckDB-compatible SQL statement via Statement Execution API and wait for completion."""
    logger.info("Executing SQL: %s", description or query.strip()[:80] + "...")
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=query,
        wait_timeout="50s",
    )

    statement_id = resp.statement_id
    status = resp.status.state

    # Poll if query hasn't completed synchronously
    while status in [StatementState.PENDING, StatementState.RUNNING]:
        time.sleep(1)
        check = w.statement_execution.get_statement(statement_id=statement_id)
        status = check.status.state

    if status != StatementState.SUCCEEDED:
        error_msg = resp.status.error.message if resp.status and resp.status.error else "Unknown execution error"
        raise RuntimeError(f"Statement failed with state {status}: {error_msg}")

    logger.info("Query finished successfully: %s", status.value)


def run_silver_transform() -> None:
    """
    Executes Silver Cleansing and Data Quality check via CTAS.
    
    CRITICAL DUCKDB & MINILAKE COMPATIBILITY NOTE:
    MiniLake uses DuckDB as its query execution engine. DuckDB has limited or
    read-only support for in-place Delta Lake UPDATE and DELETE operations.
    Therefore, the standard, robust pattern on MiniLake is Create Table As Select (CTAS)
    with DROP TABLE IF EXISTS, ensuring atomic and clean Silver layer refresh.
    """
    w = WorkspaceClient(host=MINILAKE_HOST, token=MINILAKE_TOKEN)
    warehouse_id = get_or_create_sql_warehouse(w)

    # 1. Drop existing silver clean table if exists
    drop_clean_sql = f"DROP TABLE IF EXISTS {TABLE_SILVER_CLEAN};"
    execute_sql(w, warehouse_id, drop_clean_sql, "Drop existing Silver clean table")

    # 2. CTAS Silver Cleansing
    # - Cast sale_date to DATE (DuckDB strptime/cast compatible: standard ISO YYYY-MM-DD or CAST)
    # - Cast units_sold to INTEGER
    # - Cast revenue to DECIMAL(12,2)
    # - Filter out NULLs, non-positive units_sold and revenue
    clean_sql = f"""
    CREATE TABLE {TABLE_SILVER_CLEAN} AS
    SELECT
        TRIM(drug_name) AS drug_name,
        TRIM(manufacturer) AS manufacturer,
        TRIM(dosage_form) AS dosage_form,
        TRIM(strength) AS strength,
        TRIM(package_size) AS package_size,
        CAST(units_sold AS INTEGER) AS units_sold,
        CAST(revenue AS DECIMAL(12,2)) AS revenue,
        TRY_CAST(sale_date AS DATE) AS sale_date,
        TRIM(region) AS region,
        TRIM(sales_representative) AS sales_representative,
        TRIM(customer_type) AS customer_type
    FROM {TABLE_BRONZE_RAW}
    WHERE
        drug_name IS NOT NULL
        AND units_sold IS NOT NULL
        AND revenue IS NOT NULL
        AND sale_date IS NOT NULL
        AND CAST(units_sold AS INTEGER) > 0
        AND CAST(revenue AS DECIMAL(12,2)) > 0.00;
    """
    execute_sql(w, warehouse_id, clean_sql, "CTAS pharmacy.silver.sales_clean")

    # 3. Create Data Quality (DQ) Report Table
    # MiniLake does not support Databricks Lakehouse Expectations / DLT constraints.
    # This explicit DQ table captures bronze_rows, silver_rows, dropped_rows, and validation rate.
    drop_dq_sql = f"DROP TABLE IF EXISTS {TABLE_SILVER_DQ};"
    execute_sql(w, warehouse_id, drop_dq_sql, "Drop existing Silver DQ report table")

    dq_sql = f"""
    CREATE TABLE {TABLE_SILVER_DQ} AS
    WITH bronze_stat AS (
        SELECT COUNT(*) AS bronze_rows FROM {TABLE_BRONZE_RAW}
    ),
    silver_stat AS (
        SELECT COUNT(*) AS silver_rows FROM {TABLE_SILVER_CLEAN}
    )
    SELECT
        b.bronze_rows,
        s.silver_rows,
        (b.bronze_rows - s.silver_rows) AS dropped_rows,
        ROUND((s.silver_rows * 100.0 / NULLIF(b.bronze_rows, 0)), 2) AS pass_percentage,
        CURRENT_TIMESTAMP AS evaluated_at
    FROM bronze_stat b, silver_stat s;
    """
    execute_sql(w, warehouse_id, dq_sql, "CTAS pharmacy.silver.dq_report")

    # 4. Display DQ Summary in console
    res = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=f"SELECT * FROM {TABLE_SILVER_DQ};",
        wait_timeout="30s",
    )
    if res.result and res.result.data_array:
        logger.info("DQ Report metrics [bronze_rows, silver_rows, dropped_rows, pass_pct, evaluated_at]:")
        for row in res.result.data_array:
            logger.info("DQ Output: %s", row)


if __name__ == "__main__":
    try:
        run_silver_transform()
        logger.info("Script 03 completed successfully.")
    except Exception as err:
        logger.error("Silver transform failed: %s", err)
        sys.exit(1)
