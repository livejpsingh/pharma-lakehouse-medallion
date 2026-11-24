"""Test raw data contracts and data quality validation logic."""

import csv
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import config


def test_raw_csv_schema_and_integrity():
    """Ensure raw CSV has the expected headers and non-zero record count."""
    expected_headers = [
        "drug_name",
        "manufacturer",
        "dosage_form",
        "strength",
        "package_size",
        "units_sold",
        "revenue",
        "sale_date",
        "region",
        "sales_representative",
        "customer_type",
    ]

    with open(config.RAW_DATA_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    assert headers == expected_headers, f"Header mismatch: expected {expected_headers}, got {headers}"
    assert len(rows) == 20, f"Expected 20 raw rows, found {len(rows)}"


def test_quarantined_record_filtering():
    """Verify that cleansing filters identify invalid records (negative units/revenue, empty values)."""
    with open(config.RAW_DATA_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        valid_count = 0
        dropped_count = 0

        for row in reader:
            try:
                units = int(row["units_sold"])
                rev = float(row["revenue"])
                dt = row["sale_date"].strip()
                name = row["drug_name"].strip()

                if units > 0 and rev > 0.0 and dt and name:
                    valid_count += 1
                else:
                    dropped_count += 1
            except (ValueError, TypeError):
                dropped_count += 1

    assert valid_count == 18, f"Expected 18 valid rows, got {valid_count}"
    assert dropped_count == 2, f"Expected 2 dropped rows, got {dropped_count}"
    pass_pct = round((valid_count * 100.0) / (valid_count + dropped_count), 2)
    assert pass_pct == 90.0, f"Expected 90.0% pass rate, got {pass_pct}"
