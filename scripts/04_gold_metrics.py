"""
Script 04: Gold Metrics & Power BI CSV Exports
Executes DuckDB SQL via Databricks SDK to produce 3 Gold-layer analytics tables:
  1. gold.daily_sales
  2. gold.drug_performance
  3. gold.rep_performance
Exports all three tables to /data/exports/*.csv using DuckDB's COPY statement.
"""

import logging
import sys
import time

from config import (
    DEFAULT_WAREHOUSE_NAME,
    EXPORTS_CONTAINER_PATH,
    MINILAKE_HOST,
    MINILAKE_TOKEN,
    TABLE_GOLD_DAILY_SALES,
    TABLE_GOLD_DRUG_PERF,
    TABLE_GOLD_REP_PERF,
    TABLE_SILVER_CLEAN,
)
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_or_create_sql_warehouse(w: WorkspaceClient) -> str:
    """Retrieve existing warehouse ID or create a default one."""
    warehouses = list(w.warehouses.list())
    for wh in warehouses:
        if wh.name == DEFAULT_WAREHOUSE_NAME:
            return wh.id

    created = w.warehouses.create(
        name=DEFAULT_WAREHOUSE_NAME,
        cluster_size="2X-Small",
        min_num_clusters=1,
        max_num_clusters=1,
    )
    return created.id if hasattr(created, "id") and created.id else created.result().id


def execute_sql(w: WorkspaceClient, warehouse_id: str, query: str, description: str = "") -> None:
    """Execute SQL query with polling until success."""
    logger.info("Executing: %s", description or query.strip()[:80] + "...")
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=query,
        wait_timeout="50s",
    )

    statement_id = resp.statement_id
    status = resp.status.state

    while status in [StatementState.PENDING, StatementState.RUNNING]:
        time.sleep(1)
        check = w.statement_execution.get_statement(statement_id=statement_id)
        status = check.status.state

    if status != StatementState.SUCCEEDED:
        error_msg = resp.status.error.message if resp.status and resp.status.error else "Unknown execution error"
        raise RuntimeError(f"Statement failed with state {status}: {error_msg}")

    logger.info("Successfully finished: %s", description or "Query")


def run_gold_pipeline() -> None:
    """Build Gold tables and export CSVs for Power BI Desktop."""
    w = WorkspaceClient(host=MINILAKE_HOST, token=MINILAKE_TOKEN)
    warehouse_id = get_or_create_sql_warehouse(w)

    # ---------------------------------------------------------
    # 1. Gold Table: daily_sales
    # Metrics: sale_date, region, total_revenue, total_units
    # ---------------------------------------------------------
    execute_sql(
        w,
        warehouse_id,
        f"DROP TABLE IF EXISTS {TABLE_GOLD_DAILY_SALES};",
        "Drop existing daily_sales table",
    )

    daily_sales_sql = f"""
    CREATE TABLE {TABLE_GOLD_DAILY_SALES} AS
    SELECT
        sale_date,
        region,
        ROUND(SUM(revenue), 2) AS total_revenue,
        SUM(units_sold) AS total_units,
        COUNT(*) AS transaction_count
    FROM {TABLE_SILVER_CLEAN}
    GROUP BY sale_date, region
    ORDER BY sale_date ASC, region ASC;
    """
    execute_sql(w, warehouse_id, daily_sales_sql, "CTAS pharmacy.gold.daily_sales")

    # ---------------------------------------------------------
    # 2. Gold Table: drug_performance
    # Metrics: drug_name, dosage_form, total_revenue, total_units, revenue_rank
    # Window function: RANK() OVER (ORDER BY SUM(revenue) DESC)
    # ---------------------------------------------------------
    execute_sql(
        w,
        warehouse_id,
        f"DROP TABLE IF EXISTS {TABLE_GOLD_DRUG_PERF};",
        "Drop existing drug_performance table",
    )

    drug_perf_sql = f"""
    CREATE TABLE {TABLE_GOLD_DRUG_PERF} AS
    SELECT
        drug_name,
        dosage_form,
        ROUND(SUM(revenue), 2) AS total_revenue,
        SUM(units_sold) AS total_units,
        RANK() OVER (ORDER BY SUM(revenue) DESC) AS revenue_rank
    FROM {TABLE_SILVER_CLEAN}
    GROUP BY drug_name, dosage_form
    ORDER BY revenue_rank ASC;
    """
    execute_sql(w, warehouse_id, drug_perf_sql, "CTAS pharmacy.gold.drug_performance")

    # ---------------------------------------------------------
    # 3. Gold Table: rep_performance
    # Metrics: sales_representative, order_count, total_revenue, avg_order_value
    # ---------------------------------------------------------
    execute_sql(
        w,
        warehouse_id,
        f"DROP TABLE IF EXISTS {TABLE_GOLD_REP_PERF};",
        "Drop existing rep_performance table",
    )

    rep_perf_sql = f"""
    CREATE TABLE {TABLE_GOLD_REP_PERF} AS
    SELECT
        sales_representative,
        COUNT(*) AS order_count,
        ROUND(SUM(revenue), 2) AS total_revenue,
        ROUND(AVG(revenue), 2) AS avg_order_value,
        SUM(units_sold) AS total_units
    FROM {TABLE_SILVER_CLEAN}
    GROUP BY sales_representative
    ORDER BY total_revenue DESC;
    """
    execute_sql(w, warehouse_id, rep_perf_sql, "CTAS pharmacy.gold.rep_performance")

    # ---------------------------------------------------------
    # 4. Export Gold Tables to CSV via DuckDB COPY command
    # Path: /data/exports/*.csv (mapped to local host ./exports)
    # ---------------------------------------------------------
    exports = [
        (TABLE_GOLD_DAILY_SALES, f"{EXPORTS_CONTAINER_PATH}/daily_sales.csv"),
        (TABLE_GOLD_DRUG_PERF, f"{EXPORTS_CONTAINER_PATH}/drug_performance.csv"),
        (TABLE_GOLD_REP_PERF, f"{EXPORTS_CONTAINER_PATH}/rep_performance.csv"),
    ]

    for table_name, export_path in exports:
        export_sql = f"""
        COPY {table_name} TO '{export_path}' (HEADER, DELIMITER ',');
        """
        execute_sql(w, warehouse_id, export_sql, f"Export {table_name} to {export_path}")

    logger.info("All 3 Gold tables exported successfully to %s", EXPORTS_CONTAINER_PATH)


if __name__ == "__main__":
    try:
        run_gold_pipeline()
        logger.info("Script 04 completed successfully.")
    except Exception as err:
        logger.error("Gold metrics generation failed: %s", err)
        sys.exit(1)
