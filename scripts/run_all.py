"""
Master Pipeline Orchestrator
Executes the Medallion Architecture pipeline end-to-end:
  Step 01: Setup Catalog & Medallion Schemas
  Step 02: Ingest Raw CSV to Bronze Delta Lake & Register in Unity Catalog
  Step 03: Cleanse & Evaluate Data Quality into Silver
  Step 04: Generate Gold Metrics & Export CSVs for Power BI
"""

import importlib
import logging
import sys
import time
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from config import MINILAKE_HOST

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("PipelineRunner")


def run_pipeline() -> None:
    logger.info("=================================================================")
    logger.info("Starting Medallion Architecture Pipeline on MiniLake (%s)", MINILAKE_HOST)
    logger.info("=================================================================")
    start_time = time.time()

    # Step 1: Catalog & Schemas
    logger.info(">>> Step 1/4: Initializing Catalog and Schemas...")
    mod_step1 = importlib.import_module("01_setup_catalog")
    client = mod_step1.get_workspace_client()
    mod_step1.setup_catalog_and_schemas(client)
    logger.info(">>> Step 1/4 completed.\n")

    # Step 2: Bronze Ingestion
    logger.info(">>> Step 2/4: Running Bronze Delta Lake Ingestion (PySpark)...")
    mod_step2 = importlib.import_module("02_bronze_ingest")
    mod_step2.run_bronze_ingestion()
    logger.info(">>> Step 2/4 completed.\n")

    # Step 3: Silver Transformation & DQ
    logger.info(">>> Step 3/4: Cleansing data into Silver & generating DQ Report...")
    mod_step3 = importlib.import_module("03_silver_transform")
    mod_step3.run_silver_transform()
    logger.info(">>> Step 3/4 completed.\n")

    # Step 4: Gold Analytics & CSV Export
    logger.info(">>> Step 4/4: Computing Gold layer aggregations and exporting CSVs...")
    mod_step4 = importlib.import_module("04_gold_metrics")
    mod_step4.run_gold_pipeline()
    logger.info(">>> Step 4/4 completed.\n")

    elapsed = time.time() - start_time
    logger.info("=================================================================")
    logger.info("Medallion Pipeline executed successfully in %.2f seconds!", elapsed)
    logger.info("Exported files available in ./exports/ for Power BI Desktop.")
    logger.info("=================================================================")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logger.error("Pipeline execution failed: %s", e)
        sys.exit(1)
