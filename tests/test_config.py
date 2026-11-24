"""Test pipeline configuration and path resolution."""

import sys
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import config


def test_project_paths():
    """Verify essential directory paths exist."""
    assert config.PROJECT_ROOT.exists(), "PROJECT_ROOT must exist"
    assert config.DATA_DIR.exists(), "DATA_DIR must exist"
    assert config.RAW_DATA_PATH.exists(), f"Raw dataset missing at {config.RAW_DATA_PATH}"
    assert config.EXPORTS_DIR.exists(), "EXPORTS_DIR must exist"


def test_catalog_constants():
    """Verify catalog and schema naming conventions."""
    assert config.CATALOG_NAME == "pharmacy"
    assert config.SCHEMA_BRONZE == "bronze"
    assert config.SCHEMA_SILVER == "silver"
    assert config.SCHEMA_GOLD == "gold"
    assert config.TABLE_BRONZE_RAW == "pharmacy.bronze.sales_raw"
    assert config.TABLE_SILVER_CLEAN == "pharmacy.silver.sales_clean"
