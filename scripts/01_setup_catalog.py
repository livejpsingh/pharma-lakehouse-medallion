"""
Script 01: Setup Catalog and Schemas
Creates the 'pharmacy' catalog and bronze, silver, gold schemas using Databricks SDK on MiniLake.
"""

import logging
import sys

from config import (
    CATALOG_NAME,
    MINILAKE_HOST,
    MINILAKE_TOKEN,
    SCHEMA_BRONZE,
    SCHEMA_GOLD,
    SCHEMA_SILVER,
)
from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_workspace_client() -> WorkspaceClient:
    """Instantiate Databricks WorkspaceClient pointed at local MiniLake emulator."""
    return WorkspaceClient(host=MINILAKE_HOST, token=MINILAKE_TOKEN)


def setup_catalog_and_schemas(w: WorkspaceClient) -> None:
    """Create pharmacy catalog and medallion schemas idempotently."""
    logger.info("Initializing Catalog setup on MiniLake (%s)...", MINILAKE_HOST)

    # 1. Create Catalog
    try:
        w.catalogs.create(name=CATALOG_NAME, comment="Pharmacy Sales & Inventory Analysis Catalog")
        logger.info("Catalog '%s' created successfully.", CATALOG_NAME)
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Catalog '%s' already exists.", CATALOG_NAME)
        else:
            logger.error("Failed to create catalog '%s': %s", CATALOG_NAME, e)
            raise

    # 2. Create Medallion Schemas
    schemas = [SCHEMA_BRONZE, SCHEMA_SILVER, SCHEMA_GOLD]
    for schema_name in schemas:
        try:
            w.schemas.create(
                name=schema_name,
                catalog_name=CATALOG_NAME,
                comment=f"{schema_name.capitalize()} layer schema for pharmacy analytics",
            )
            logger.info("Schema '%s.%s' created successfully.", CATALOG_NAME, schema_name)
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Schema '%s.%s' already exists.", CATALOG_NAME, schema_name)
            else:
                logger.error("Failed to create schema '%s.%s': %s", CATALOG_NAME, schema_name, e)
                raise


if __name__ == "__main__":
    try:
        client = get_workspace_client()
        setup_catalog_and_schemas(client)
        logger.info("Script 01 completed successfully.")
    except Exception as err:
        logger.error("Execution failed: %s", err)
        sys.exit(1)
