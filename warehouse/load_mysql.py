"""
warehouse/load_mysql.py
=======================
Loads all warehouse CSV files into MySQL insurance_dw database.

Prerequisites:
    pip install mysql-connector-python pandas

MySQL setup:
    1. Run warehouse/schema.sql first to create DB + tables
    2. Update DB_CONFIG below with your MySQL credentials

Usage:
    python warehouse/load_mysql.py
"""

import os
import sys
import pandas as pd
import numpy as np

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WH_DIR = os.path.join(ROOT, "output", "warehouse")

# ── MySQL Configuration ─────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "your_password_here",    # ← change this
    "database": "insurance_dw",
}

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️  mysql-connector-python not installed.")
    print("   Run: pip install mysql-connector-python")
    print("   Continuing with dry-run mode (showing row counts only).\n")


def clean_value(v):
    """Convert NaN/NaT/empty to None for MySQL."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, str) and v.strip() in ("", "nan", "NaT", "None"):
        return None
    return v


def load_table(conn, table_name: str, df: pd.DataFrame, pk_col: str = None):
    """
    Load a DataFrame into a MySQL table.
    Uses INSERT IGNORE to skip duplicate PKs.
    """
    if df is None or len(df) == 0:
        print(f"  ⚠️  {table_name}: empty, skipping")
        return

    cursor = conn.cursor()
    cols   = list(df.columns)
    placeholders = ", ".join(["%s"] * len(cols))
    col_names    = ", ".join([f"`{c}`" for c in cols])
    sql = f"INSERT IGNORE INTO `{table_name}` ({col_names}) VALUES ({placeholders})"

    rows_loaded = 0
    rows_skipped = 0

    for _, row in df.iterrows():
        values = tuple(clean_value(row[c]) for c in cols)
        try:
            cursor.execute(sql, values)
            rows_loaded += 1
        except Exception as e:
            rows_skipped += 1
            if rows_skipped <= 3:
                print(f"    ⚠️  Row skipped: {e}")

    conn.commit()
    cursor.close()
    print(f"  ✅  {table_name:25s}: {rows_loaded:6,} rows loaded, {rows_skipped} skipped")


def dry_run():
    """Show what would be loaded without MySQL."""
    print("\n=== DRY RUN (MySQL not connected) ===\n")
    for fname in sorted(os.listdir(WH_DIR)):
        if fname.endswith(".csv"):
            path = os.path.join(WH_DIR, fname)
            df   = pd.read_csv(path)
            tbl  = fname.replace(".csv","")
            print(f"  {tbl:40s} → {len(df):6,} rows   columns: {list(df.columns[:4])}...")


def run_load():
    if not MYSQL_AVAILABLE:
        dry_run()
        return

    print("\n=== Connecting to MySQL ===")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print(f"  ✅  Connected to {DB_CONFIG['host']}:{DB_CONFIG['port']} / {DB_CONFIG['database']}")
    except Exception as e:
        print(f"  ❌  Connection failed: {e}")
        print("\nFalling back to dry-run mode:")
        dry_run()
        return

    print("\n=== Loading Dimension Tables ===")

    # dim_customer
    df = pd.read_csv(os.path.join(WH_DIR, "dim_customer.csv"))
    df["DOB"]                = pd.to_datetime(df["DOB"], errors="coerce").dt.date
    df["Effective_Start_Dt"] = pd.to_datetime(df["Effective_Start_Dt"], errors="coerce").dt.date
    df["Effective_End_Dt"]   = pd.to_datetime(df["Effective_End_Dt"], errors="coerce").dt.date
    load_table(conn, "dim_customer", df)

    # dim_policy
    df = pd.read_csv(os.path.join(WH_DIR, "dim_policy.csv"))
    for dc in ["Policy_Start_Dt","Policy_End_Dt","Next_Premium_Dt","Actual_Premium_Paid_Dt"]:
        df[dc] = pd.to_datetime(df[dc], errors="coerce").dt.date
    load_table(conn, "dim_policy", df)

    # dim_address
    df = pd.read_csv(os.path.join(WH_DIR, "dim_address.csv"))
    load_table(conn, "dim_address", df)

    print("\n=== Loading Fact Table ===")

    # fact_transactions
    df = pd.read_csv(os.path.join(WH_DIR, "fact_transactions.csv"))
    for dc in ["Actual_Premium_Paid_Dt","Next_Premium_Dt"]:
        df[dc] = pd.to_datetime(df[dc], errors="coerce").dt.date
    load_table(conn, "fact_transactions", df)

    conn.close()
    print("\n✅  All tables loaded successfully into insurance_dw.")
    print(f"    You can now run the SQL views from warehouse/schema.sql (queries b–g).")


if __name__ == "__main__":
    run_load()
