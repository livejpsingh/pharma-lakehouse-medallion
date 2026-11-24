"""
Pharmacy Sales & Inventory Risk Analysis - Pipeline Configuration
Centralized configuration for local Medallion Architecture on MiniLake.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base Paths (Local host and container alignment)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
RAW_DATA_PATH = DATA_DIR / "raw" / "pharma_sales.csv"
EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", str(PROJECT_ROOT / "exports")))

# MiniLake Connection Settings
MINILAKE_HOST = os.getenv("MINILAKE_HOST", "http://localhost:8000")
MINILAKE_TOKEN = os.getenv("MINILAKE_TOKEN", "dev")
DEFAULT_WAREHOUSE_NAME = os.getenv("DEFAULT_WAREHOUSE_NAME", "local-duckdb-warehouse")

# Delta Storage Location (Inside MiniLake container / host volume mount)
CONTAINER_DATA_ROOT = os.getenv("CONTAINER_DATA_ROOT", "/data")
DELTA_BRONZE_PATH = f"{CONTAINER_DATA_ROOT}/delta/pharmacy/bronze/sales_raw"
EXPORTS_CONTAINER_PATH = f"{CONTAINER_DATA_ROOT}/exports"

# Unity Catalog / MiniLake Hierarchy
CATALOG_NAME = "pharmacy"
SCHEMA_BRONZE = "bronze"
SCHEMA_SILVER = "silver"
SCHEMA_GOLD = "gold"

# Table Names
TABLE_BRONZE_RAW = f"{CATALOG_NAME}.{SCHEMA_BRONZE}.sales_raw"
TABLE_SILVER_CLEAN = f"{CATALOG_NAME}.{SCHEMA_SILVER}.sales_clean"
TABLE_SILVER_DQ = f"{CATALOG_NAME}.{SCHEMA_SILVER}.dq_report"
TABLE_GOLD_DAILY_SALES = f"{CATALOG_NAME}.{SCHEMA_GOLD}.daily_sales"
TABLE_GOLD_DRUG_PERF = f"{CATALOG_NAME}.{SCHEMA_GOLD}.drug_performance"
TABLE_GOLD_REP_PERF = f"{CATALOG_NAME}.{SCHEMA_GOLD}.rep_performance"
