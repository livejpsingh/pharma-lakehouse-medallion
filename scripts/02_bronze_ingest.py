"""
Script 02: Bronze Ingest
Ingests raw pharmacy sales CSV via PySpark with inferSchema=False.
Writes Delta lake table to /data/delta/pharmacy/bronze/sales_raw (overwrite mode).
Registers EXTERNAL Delta table pharmacy.bronze.sales_raw via Databricks SDK.
"""

import logging
import sys

from config import (
    CATALOG_NAME,
    DELTA_BRONZE_PATH,
    MINILAKE_HOST,
    MINILAKE_TOKEN,
    RAW_DATA_PATH,
    SCHEMA_BRONZE,
    TABLE_BRONZE_RAW,
)
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import (
    ColumnInfo,
    ColumnTypeName,
    DataSourceFormat,
    TableType,
)
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_spark_session() -> SparkSession:
    """Build Spark session configured for Delta Lake and Unity Catalog interop."""
    builder = (
        SparkSession.builder.appName("PharmacyBronzeIngest")
        .master("local[*]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def register_external_delta_table(w: WorkspaceClient, df_schema) -> None:
    """
    Registers the Delta table as an EXTERNAL DELTA table in MiniLake Unity Catalog.
    
    CRITICAL ARCHITECTURAL NOTE:
    MiniLake MANAGED tables are DuckDB-native internal tables stored in DuckDB's
    private storage format, making them INVISIBLE to Spark engines.
    To allow Spark and DuckDB to interoperate seamlessly on the same data lake,
    all tables that Spark writes must be registered as:
      table_type = EXTERNAL
      data_source_format = DELTA
      storage_location = /data/... (or container mounted path)
    """
    logger.info("Registering EXTERNAL DELTA table '%s' via Databricks SDK...", TABLE_BRONZE_RAW)

    # Clean existing registration if already present
    try:
        w.tables.delete(full_name=TABLE_BRONZE_RAW)
        logger.info("Existing table registration '%s' dropped.", TABLE_BRONZE_RAW)
    except Exception:
        pass

    # Map PySpark string fields to Unity Catalog columns
    columns = [
        ColumnInfo(name=field.name, type_name=ColumnTypeName.STRING, type_text="string", position=idx, nullable=True)
        for idx, field in enumerate(df_schema.fields)
    ]

    try:
        w.tables.create(
            name="sales_raw",
            catalog_name=CATALOG_NAME,
            schema_name=SCHEMA_BRONZE,
            table_type=TableType.EXTERNAL,
            data_source_format=DataSourceFormat.DELTA,
            storage_location=DELTA_BRONZE_PATH,
            columns=columns,
        )
        logger.info("Successfully registered EXTERNAL DELTA table '%s'.", TABLE_BRONZE_RAW)
    except Exception as e:
        logger.error("Failed to register EXTERNAL DELTA table: %s", e)
        raise


def run_bronze_ingestion() -> None:
    """Read raw CSV without schema inference, write idempotent Delta, and register catalog."""
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Source raw data file not found at: {RAW_DATA_PATH}. "
            f"Please place 'Sample_Pharmaceutical_Drug_Sales.csv' in data/raw/pharma_sales.csv."
        )

    logger.info("Starting Bronze Ingestion from: %s", RAW_DATA_PATH)
    spark = create_spark_session()

    try:
        # Read raw CSV with inferSchema=False (all fields ingested as pure strings)
        raw_df = (
            spark.read.format("csv")
            .option("header", "true")
            .option("inferSchema", "false")
            .load(str(RAW_DATA_PATH))
        )

        row_count = raw_df.count()
        logger.info("Read %d rows from raw CSV. Writing Delta to %s...", row_count, DELTA_BRONZE_PATH)

        # Write to Delta Lake directory idempotently (mode overwrite)
        raw_df.write.format("delta").mode("overwrite").save(DELTA_BRONZE_PATH)
        logger.info("Delta write completed successfully.")

        # Register external table in MiniLake
        sdk_client = WorkspaceClient(host=MINILAKE_HOST, token=MINILAKE_TOKEN)
        register_external_delta_table(sdk_client, raw_df.schema)

    finally:
        spark.stop()
        logger.info("Spark session stopped.")


if __name__ == "__main__":
    try:
        run_bronze_ingestion()
        logger.info("Script 02 completed successfully.")
    except Exception as err:
        logger.error("Bronze ingestion failed: %s", err)
        sys.exit(1)
