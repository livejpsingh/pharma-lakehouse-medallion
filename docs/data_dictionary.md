# Data Dictionary

Comprehensive schema documentation for all Medallion Lakehouse layers (`Bronze`, `Silver`, and `Gold`), including data types, nullability, business descriptions, and constraints.

---

## 1. Raw Source Dataset (`data/raw/pharma_sales.csv`)

| Column Name | Raw Ingest Type | Nullable | Example Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| `drug_name` | `STRING` | No | `"Lipitor"` | Commercial trade name of pharmaceutical medication. |
| `manufacturer` | `STRING` | No | `"Pfizer"` | Drug manufacturing pharmaceutical enterprise. |
| `dosage_form` | `STRING` | No | `"Tablet"` | Physical dispensing form (`Tablet`, `Capsule`, `Inhaler`). |
| `strength` | `STRING` | No | `"20mg"` | Active ingredient strength per dispensing unit. |
| `package_size` | `STRING` | No | `"30 tabs"` | Pack size quantity and packaging descriptor. |
| `units_sold` | `STRING` | Yes | `"120"` | Untyped quantity sold (may contain negative numbers or nulls in raw). |
| `revenue` | `STRING` | Yes | `"3840.00"` | Untyped total sales transaction revenue amount (USD). |
| `sale_date` | `STRING` | No | `"2024-01-15"` | Calendar date of sales transaction (`YYYY-MM-DD`). |
| `region` | `STRING` | No | `"East"` | Regional sales territory (`East`, `West`, `North`, `South`). |
| `sales_representative` | `STRING` | No | `"Michael Chang"` | Name of territory medical sales account representative. |
| `customer_type` | `STRING` | No | `"Retail Pharmacy"` | Channel segment (`Hospital`, `Clinic`, `Retail Pharmacy`). |

---

## 2. Bronze Layer: Raw Storage (`pharmacy.bronze.sales_raw`)

- **Table Type**: `EXTERNAL DELTA`
- **Underlying Storage**: Parquet with Delta transaction log (`/data/delta/pharmacy/bronze/sales_raw/`)
- **Ingestion Policy**: `inferSchema=False` (100% string preservation to prevent ingestion dropouts or unhandled casting exceptions).

| Column Name | Unity Catalog Type | Description |
| :--- | :--- | :--- |
| `drug_name` | `STRING` | Raw untyped medication name. |
| `manufacturer` | `STRING` | Raw untyped manufacturer. |
| `dosage_form` | `STRING` | Raw untyped dosage format. |
| `strength` | `STRING` | Raw untyped strength. |
| `package_size` | `STRING` | Raw untyped packaging descriptor. |
| `units_sold` | `STRING` | String representation of volume. |
| `revenue` | `STRING` | String representation of monetary revenue. |
| `sale_date` | `STRING` | String representation of transaction date. |
| `region` | `STRING` | String representation of sales region. |
| `sales_representative`| `STRING` | String representation of representative. |
| `customer_type` | `STRING` | String representation of customer channel. |

---

## 3. Silver Layer: Cleaned & Validated (`pharmacy.silver.sales_clean`)

- **Table Type**: DuckDB Managed Table (persisted via CTAS)
- **Validation Rules**: `units_sold > 0`, `revenue > 0.00`, non-null dates, trimmed string whitespace.

| Column Name | SQL / DuckDB Data Type | Nullable | Description & Constraints |
| :--- | :--- | :--- | :--- |
| `drug_name` | `VARCHAR` | No | Cleaned, whitespace-trimmed medication name. |
| `manufacturer` | `VARCHAR` | No | Cleaned, whitespace-trimmed manufacturer name. |
| `dosage_form` | `VARCHAR` | No | Standardized dosage form (`Tablet`, `Capsule`, `Inhaler`). |
| `strength` | `VARCHAR` | No | Standardized strength specification. |
| `package_size` | `VARCHAR` | No | Standardized package descriptor. |
| `units_sold` | `INTEGER` | No | Strictly positive integer units sold (`> 0`). |
| `revenue` | `DECIMAL(12,2)` | No | Strictly positive sales amount in USD (`> 0.00`). |
| `sale_date` | `DATE` | No | ISO standard date (`YYYY-MM-DD`), verified by `TRY_CAST`. |
| `region` | `VARCHAR` | No | Validated territory (`North`, `South`, `East`, `West`). |
| `sales_representative`| `VARCHAR` | No | Validated sales representative. |
| `customer_type` | `VARCHAR` | No | Validated customer classification. |

---

## 4. Silver Observability: Quality Report (`pharmacy.silver.dq_report`)

Tracks pipeline audit metrics across each batch run.

| Column Name | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `bronze_rows` | `BIGINT` | `20` | Count of records ingested into the Bronze layer. |
| `silver_rows` | `BIGINT` | `18` | Count of records passing validation into Silver. |
| `dropped_rows` | `BIGINT` | `2` | Corrupted/quarantined records excluded from Silver. |
| `pass_percentage` | `DECIMAL(5,2)` | `90.00` | Percentage of clean records (`silver_rows / bronze_rows * 100`). |
| `evaluated_at` | `TIMESTAMP` | `2024-11-24 12:54:48` | Audit execution timestamp (UTC). |

---

## 5. Gold Layer Analytics Tables

### Table 5.1: `pharmacy.gold.daily_sales`
Aggregates sales trends per calendar date and geographical region.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `sale_date` | `DATE` | Calendar transaction date. |
| `region` | `VARCHAR` | Regional sales territory. |
| `total_revenue` | `DECIMAL(14,2)`| Net aggregated revenue (`ROUND(SUM(revenue), 2)`). |
| `total_units` | `BIGINT` | Total quantity sold (`SUM(units_sold)`). |
| `transaction_count` | `BIGINT` | Number of sales orders logged on this date/region. |

### Table 5.2: `pharmacy.gold.drug_performance`
Ranks pharmaceutical product revenue using window functions.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `drug_name` | `VARCHAR` | Medication commercial name. |
| `dosage_form` | `VARCHAR` | Product formulation. |
| `total_revenue` | `DECIMAL(14,2)`| Total revenue generated across all regions. |
| `total_units` | `BIGINT` | Total units dispensed. |
| `revenue_rank` | `BIGINT` | Dense rank calculated via `RANK() OVER (ORDER BY SUM(revenue) DESC)`. |

### Table 5.3: `pharmacy.gold.rep_performance`
Calculates commercial sales performance metrics per sales representative.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `sales_representative`| `VARCHAR` | Full name of sales representative. |
| `order_count` | `BIGINT` | Total count of closed sales transactions. |
| `total_revenue` | `DECIMAL(14,2)`| Cumulative sales revenue generated in USD. |
| `avg_order_value` | `DECIMAL(14,2)`| Average deal size (`ROUND(AVG(revenue), 2)`). |
| `total_units` | `BIGINT` | Cumulative units delivered. |
