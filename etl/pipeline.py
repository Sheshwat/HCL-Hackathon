"""
etl/pipeline.py
===============
Master ETL Pipeline Orchestrator
Processes day0 → day1 → day2 incrementally.

Usage:
    python etl/pipeline.py

Output:
    output/cleaned/   → cleaned + transformed CSV files per day
    output/logs/      → validation reports
    output/warehouse/ → final warehouse tables (dim + fact)
"""

import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime

# Make sure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from etl.validation      import run_validation
from etl.standardization import run_standardization
from etl.transformation  import run_transformation

# ── Logging ────────────────────────────────────────────────────────
LOG_DIR = os.path.join(ROOT, "output", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), mode="w"),
    ]
)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────
SRC_DIR  = os.path.join(ROOT, "source_data")
OUT_DIR  = os.path.join(ROOT, "output", "cleaned")
WH_DIR   = os.path.join(ROOT, "output", "warehouse")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(WH_DIR, exist_ok=True)

DAYS = ["day0", "day1", "day2"]


def load_day(day: str) -> dict:
    """Load all 4 CSV files for a given day into DataFrames."""
    logger.info(f"\n{'='*60}")
    logger.info(f"  LOADING {day.upper()}")
    logger.info(f"{'='*60}")

    tables = {}
    for table in ["customers", "policies", "address", "transactions"]:
        path = os.path.join(SRC_DIR, f"{day}_{table}.csv")
        if not os.path.exists(path):
            logger.warning(f"  File not found: {path} — skipping")
            tables[table] = pd.DataFrame()
            continue
        df = pd.read_csv(path, dtype=str)   # read all as string first
        logger.info(f"  Loaded {table}: {len(df)} rows from {os.path.basename(path)}")
        tables[table] = df

    return tables


def save_cleaned(day: str, data: dict):
    """Save validated+standardized DataFrames to output/cleaned/."""
    for table, df in data.items():
        if df is not None and len(df) > 0:
            path = os.path.join(OUT_DIR, f"{day}_{table}_clean.csv")
            df.to_csv(path, index=False)
            logger.info(f"  Saved: {os.path.basename(path)} ({len(df)} rows)")


def save_warehouse(transformed: dict, day: str):
    """
    Append/upsert transformed tables into the warehouse CSVs.
    dim tables  → upsert on surrogate key
    fact table  → append
    """
    for tbl in ["dim_customer", "dim_policy", "dim_address"]:
        df_new  = transformed.get(tbl)
        if df_new is None or len(df_new) == 0:
            continue
        path = os.path.join(WH_DIR, f"{tbl}.csv")
        if os.path.exists(path):
            df_exist = pd.read_csv(path)
            df_all   = pd.concat([df_exist, df_new], ignore_index=True)
        else:
            df_all = df_new
        df_all.to_csv(path, index=False)
        logger.info(f"  Warehouse {tbl}: {len(df_all)} total rows")

    # Fact — always append
    df_fact = transformed.get("fact_transactions")
    if df_fact is not None and len(df_fact) > 0:
        path = os.path.join(WH_DIR, "fact_transactions.csv")
        if os.path.exists(path):
            df_exist = pd.read_csv(path)
            df_all   = pd.concat([df_exist, df_fact], ignore_index=True)
        else:
            df_all = df_fact
        df_all.to_csv(path, index=False)
        logger.info(f"  Warehouse fact_transactions: {len(df_all)} total rows")

    # Save SCD change tables
    for scd in ["policy_changes", "marital_changes"]:
        df_scd = transformed.get(scd)
        if df_scd is not None and len(df_scd) > 0:
            path = os.path.join(WH_DIR, f"{scd}_{day}.csv")
            df_scd.to_csv(path, index=False)
            logger.info(f"  SCD saved: {os.path.basename(path)} ({len(df_scd)} rows)")


def print_validation_report(reports: list):
    logger.info("\n  ── Validation Report ──")
    for r in reports:
        status = "✅" if r["issues"] == ["All checks passed."] else "⚠️ "
        logger.info(f"  {status}  {r['table']:15s}  "
                    f"in={r['rows_in']:5d}  out={r['rows_out']:5d}  "
                    f"| {'; '.join(r['issues'][:2])}")


def run_pipeline():
    logger.info(f"\n{'#'*60}")
    logger.info(f"  INSURANCE POLICY DATA ENGINEERING PIPELINE")
    logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'#'*60}")

    prev_day_policies = None
    all_reports       = {}

    for day in DAYS:
        # ── 1. Ingest ───────────────────────────────────────────────
        raw_data = load_day(day)

        # Skip if no data
        if all(len(df) == 0 for df in raw_data.values()):
            logger.warning(f"No data found for {day}, skipping.")
            continue

        # ── 2. Validate ─────────────────────────────────────────────
        logger.info(f"\n  → Validation Stage [{day}]")
        validated, reports = run_validation(raw_data)
        print_validation_report(reports)
        all_reports[day] = reports

        # ── 3. Standardize ──────────────────────────────────────────
        logger.info(f"\n  → Standardization Stage [{day}]")
        standardized = run_standardization(validated)

        # ── 4. Save cleaned ─────────────────────────────────────────
        save_cleaned(day, standardized)

        # ── 5. Transform ────────────────────────────────────────────
        logger.info(f"\n  → Transformation Stage [{day}]")
        transformed = run_transformation(standardized, prev_day_policies)

        # ── 6. Load to Warehouse ────────────────────────────────────
        logger.info(f"\n  → Loading to Warehouse [{day}]")
        save_warehouse(transformed, day)

        # Pass policies forward for SCD detection in next day
        prev_day_policies = standardized["policies"]

        logger.info(f"\n  ✅  {day.upper()} complete.\n")

    # ── Final warehouse summary ─────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info("  FINAL WAREHOUSE SUMMARY")
    logger.info(f"{'='*60}")
    for fname in sorted(os.listdir(WH_DIR)):
        fpath = os.path.join(WH_DIR, fname)
        df    = pd.read_csv(fpath)
        logger.info(f"  {fname:40s} → {len(df):6d} rows")

    # Save JSON validation report
    report_path = os.path.join(LOG_DIR, "validation_report.json")
    with open(report_path, "w") as f:
        json.dump(all_reports, f, indent=2, default=str)
    logger.info(f"\n  Validation report saved: {report_path}")

    logger.info(f"\n{'#'*60}")
    logger.info("  PIPELINE COMPLETED SUCCESSFULLY")
    logger.info(f"{'#'*60}\n")


if __name__ == "__main__":
    run_pipeline()
