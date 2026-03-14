# ABC Insurance — Data Engineering Pipeline

## Use Case
ABC Insurance Service Provider covers all US regions.
This pipeline collects daily regional CSV data, validates and transforms it,
loads it into a dimensional data warehouse, and answers 6 key business queries.

---

## Project Structure

```
insurance_pipeline/
│
├── source_data/              ← 12 source CSV files (4 tables × 3 days)
│   ├── day0_customers.csv
│   ├── day0_policies.csv
│   ├── day0_address.csv
│   ├── day0_transactions.csv
│   ├── day1_*.csv            ← incremental updates
│   └── day2_*.csv            ← further updates
│
├── etl/
│   ├── validation.py         ← Stage 2: null/dup/type/range checks
│   ├── standardization.py    ← Stage 3: normalize regions/dates/text
│   ├── transformation.py     ← Stage 4: late fees, installments, SCD, dim/fact
│   └── pipeline.py           ← Master orchestrator (day0 → day1 → day2)
│
├── warehouse/
│   ├── schema.sql            ← MySQL DDL: all tables + analytics views
│   └── load_mysql.py         ← Loader: CSV → MySQL
│
├── analytics/
│   └── queries.py            ← All 6 business queries (b–g)
│
├── scripts/
│   ├── generate_source_data.py  ← Source data generator
│   └── build_dashboard.py       ← HTML dashboard builder
│
├── output/
│   ├── cleaned/              ← Validated + standardized CSVs per day
│   ├── warehouse/            ← Final dim/fact tables as CSVs
│   ├── analytics/            ← Query result CSVs
│   ├── logs/                 ← Pipeline log + validation JSON report
│   └── insurance_dashboard.html  ← Interactive dashboard
│
└── run_all.py               ← One-command full pipeline runner
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install pandas

# 2. Run the entire pipeline
python run_all.py

# 3. Open the dashboard
open output/insurance_dashboard.html
```

---

## Pipeline Stages

### Stage 1 — Data Ingestion
- Reads 4 CSV files per day (customers, policies, address, transactions)
- Each file contains a `Region` column (EAST/WEST/NORTH/SOUTH)
- 3 days simulated: day0 (full load), day1 & day2 (incremental)

### Stage 2 — Data Validation
| Check | What it does |
|-------|-------------|
| Schema | Ensures required columns exist |
| Null check | Drops rows with null Customer_ID, Policy_Id, Region |
| Duplicate removal | `drop_duplicates()` on primary keys |
| Type validation | Numeric coercion with `errors='coerce'` |
| Range check | Premium_Amt must be > 0 |
| Date validation | Invalid dates dropped |

### Stage 3 — Data Standardization
| Problem | Standardized to |
|---------|----------------|
| east/East/EAST/ea | EAST |
| married/m/M | Married |
| monthly/mo/month | Monthly |
| Different date formats | YYYY-MM-DD |
| Extra whitespace | Stripped |
| Mixed case names | Title Case |

### Stage 4 — Business Transformation
- **Late fee**: `Late_Fee = Premium_Amt × 2%` (when paid after due date)
- **Installments**: Monthly→12, Quarterly→4, Annual→1
- **SCD detection**: Tracks policy type changes and marital status changes
- **Dimensional modeling**: Builds dim_customer, dim_policy, dim_address, fact_transactions

---

## Analytics Queries (b–g)

| Query | Description |
|-------|-------------|
| **b** | Customers who changed policy type (current + previous) |
| **c** | Total policy amount by all customers across all regions |
| **d** | Total policy amount — Auto policy customers only |
| **e** | East+West customers with Quarterly term, policy start 2012 |
| **f** | Customers whose marital status changed (SCD Type 2) |
| **g** | All regions — full customer + policy + address + transaction view |

---

## MySQL Setup

```bash
# Install connector
pip install mysql-connector-python

# Run DDL
mysql -u root -p < warehouse/schema.sql

# Update credentials in warehouse/load_mysql.py, then:
python warehouse/load_mysql.py

# Run analytics views
mysql -u root -p insurance_dw
> SELECT * FROM vw_policy_changes LIMIT 10;
> SELECT * FROM vw_total_policy_all LIMIT 10;
> SELECT * FROM vw_auto_policy_amount LIMIT 10;
> SELECT * FROM vw_east_west_quarterly_2012;
> SELECT * FROM vw_marital_changes;
> SELECT * FROM vw_all_regions_full LIMIT 20;
```

---

## Data Warehouse Schema

```
dim_customer    (Customer_SK PK, Customer_ID, Marital_Status, Effective_Start/End_Dt, ...)
dim_policy      (Policy_SK PK, Policy_Id, Policy_Type, Policy_Term, Premium_Amt, ...)
dim_address     (Address_SK PK, Customer_ID, Country, Region, State, City, ...)
fact_transactions (Transaction_SK PK, Customer_SK FK, Policy_SK FK, Address_SK FK,
                   Premium_Amt, Total_Policy_Amt, Is_Late, Late_Fee, ...)
```

---

## Technologies Used
- Python 3.x
- pandas
- CSV files (source + warehouse)
- MySQL (optional — schema + views included)
- HTML/CSS/JS (dashboard)
