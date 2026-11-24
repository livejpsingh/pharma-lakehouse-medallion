"""Test exported Gold layer datasets for Power BI Desktop ingestion."""

import csv
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import config


def test_exported_csv_schemas():
    """Verify exported Gold CSVs exist and contain valid headers when generated."""
    daily_sales_path = config.EXPORTS_DIR / "daily_sales.csv"
    drug_perf_path = config.EXPORTS_DIR / "drug_performance.csv"
    rep_perf_path = config.EXPORTS_DIR / "rep_performance.csv"

    assert daily_sales_path.exists(), f"Missing export: {daily_sales_path}"
    with open(daily_sales_path, mode="r", encoding="utf-8") as f:
        headers = next(csv.reader(f))
        assert headers == ["sale_date", "region", "total_revenue", "total_units", "transaction_count"]

    assert drug_perf_path.exists(), f"Missing export: {drug_perf_path}"
    with open(drug_perf_path, mode="r", encoding="utf-8") as f:
        headers = next(csv.reader(f))
        assert headers == ["drug_name", "dosage_form", "total_revenue", "total_units", "revenue_rank"]

    assert rep_perf_path.exists(), f"Missing export: {rep_perf_path}"
    with open(rep_perf_path, mode="r", encoding="utf-8") as f:
        headers = next(csv.reader(f))
        assert headers == ["sales_representative", "order_count", "total_revenue", "avg_order_value", "total_units"]
