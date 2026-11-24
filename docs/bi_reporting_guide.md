# Business Intelligence & Reporting Guide

This guide outlines how to consume, visualize, and analyze the outputs of the **Pharma Lakehouse Medallion Pipeline** across multiple reporting interfaces:
1. **Interactive HTML Web Dashboard** (`dashboard/index.html`)
2. **Microsoft Power BI Desktop**
3. **MiniLake Unified Web UI** (`http://localhost:8000`)

---

## 1. Analytical Gold Datasets

The pipeline exports three pre-aggregated, business-ready CSV files in `data/exports/`:

| Dataset | Granularity | Key Metrics |
|---|---|---|
| **`daily_sales.csv`** | Date &times; Category &times; Channel | Total Revenue, Total Units Sold, Order Count, Average Order Value (AOV) |
| **`drug_performance.csv`** | Drug Name &times; Category | Total Revenue, Total Units, Unit Price, Revenue Rank, Return Rate % |
| **`rep_performance.csv`** | Sales Representative &times; Region | Total Revenue, Target Attainment %, Total Units Sold, Order Count, Rep Rank |

---

## 2. Interactive Web Dashboard (`dashboard/index.html`)

For immediate local or web reporting without requiring external software licenses:

### How to Launch:
1. Open [dashboard/index.html](file:///c:/workspace/public/pharma-lakehouse-medallion/dashboard/index.html) directly in any modern browser (Chrome, Edge, Firefox, Safari).
2. Or serve it locally:
   ```bash
   python -m http.server 3000 --directory dashboard
   ```
   Then navigate to `http://localhost:3000`.

### Key Features:
- **Executive KPI Cards**: Real-time display of Total Revenue ($148,630.00), Units Sold (1,714), Completed Orders (18), and Data Quality Pass Rate (90.0%).
- **Multi-Tab Views**:
  - **Overview**: Revenue timeline, category breakdown donut, channel distribution.
  - **Drug Analytics**: Product-level revenue ranking, units sold, and return rate indicators.
  - **Sales Rep Performance**: Target attainment % progress bars, rep tier rankings, and regional revenue.
  - **Data Quality Audit**: Summary of Bronze vs Silver records, dropped row counters, and validation rules.
- **Responsive Layout**: Powered by Tailwind CSS with SVG data visualizations and tab switching.

---

## 3. Microsoft Power BI Desktop Walkthrough

### Step 1: Connecting to Data
1. Launch Power BI Desktop.
2. Select **Get Data** &rarr; **Text/CSV**.
3. Load the following files from your local repository `data/exports/`:
   - `data/exports/daily_sales.csv`
   - `data/exports/drug_performance.csv`
   - `data/exports/rep_performance.csv`
4. In Power Query, verify:
   - `sale_date` is detected as **Date**.
   - `total_revenue`, `avg_order_value`, `target_attainment_pct` are **Decimal Number**.
   - `total_units`, `order_count`, `revenue_rank` are **Whole Number**.
5. Click **Close & Apply**.

### Step 2: Creating DAX Measures

Add the following DAX calculations to your model:

```dax
// Total Pipeline Revenue
Total Revenue = SUM(daily_sales[total_revenue])

// Total Volume of Units Sold
Total Units = SUM(daily_sales[total_units])

// Average Order Value
Overall AOV = DIVIDE([Total Revenue], SUM(daily_sales[order_count]), 0)

// High Performer Flag (Reps exceeding target)
Target Attainment Status = 
IF(
    SELECTEDVALUE(rep_performance[target_attainment_pct]) >= 100.0,
    "Target Achieved",
    "Below Target"
)
```

### Step 3: Recommended Visual Layout

```
+-------------------------------------------------------------------------------+
| [Card: Total Revenue]  [Card: Total Units]  [Card: Orders]  [Card: DQ Rate]   |
+---------------------------------------+---------------------------------------+
| Line Chart: Daily Revenue by Channel  | Clustered Bar: Top Drugs by Revenue   |
| X-Axis: sale_date                     | Y-Axis: drug_name                     |
| Y-Axis: total_revenue                 | X-Axis: total_revenue                 |
| Legend: channel                       | Tooltip: total_units, return_rate_pct |
+---------------------------------------+---------------------------------------+
| Bar Chart: Rep Target Attainment %    | Donut Chart: Revenue by Category      |
| Y-Axis: sales_rep_name                | Legend: category                      |
| X-Axis: target_attainment_pct         | Values: total_revenue                 |
| Color: Status (Green >= 100%, Orange) |                                       |
+---------------------------------------+---------------------------------------+
```

---

## 4. MiniLake Unified Web UI

MiniLake exposes an embedded Databricks Workspace & Catalog browser at `http://localhost:8000`:

1. **Catalog Explorer**:
   - Navigate to `Catalog` &rarr; `pharmacy` &rarr; `bronze` / `silver` / `gold`.
   - Inspect schemas, column data types, table properties, and storage locations.
2. **Interactive SQL Editor**:
   - Query tables directly using DuckDB SQL syntax:
   ```sql
   -- Top 5 revenue-generating drugs
   SELECT drug_name, category, total_revenue, revenue_rank
   FROM pharmacy.gold.drug_performance
   ORDER BY revenue_rank ASC
   LIMIT 5;
   ```
   - Inspect the Data Quality Audit table:
   ```sql
   SELECT * FROM pharmacy.silver.dq_report;
   ```
