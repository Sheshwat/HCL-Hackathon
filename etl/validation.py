"""
etl/validation.py
=================
Data Validation Stage
Checks: nulls, duplicates, data types, range constraints.
Returns a clean DataFrame and a validation report dict.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def validate_customers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"table": "customers", "issues": [], "rows_in": len(df), "rows_out": None}

    # 1. Required columns
    required = ["Customer_ID", "Customer_First_Name", "Customer_Last_Name",
                "Customer_Segment", "Marital_Status", "Gender", "DOB",
                "Effective_Start_Dt", "Region"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        report["issues"].append(f"Missing columns: {missing_cols}")
        logger.warning(f"[VALIDATION] customers missing columns: {missing_cols}")

    # 2. Null check on critical fields
    for col in ["Customer_ID", "Customer_First_Name", "Customer_Last_Name", "Region"]:
        if col in df.columns:
            nulls = df[col].isna().sum()
            if nulls:
                report["issues"].append(f"{col}: {nulls} null values found → dropped")
                logger.warning(f"[VALIDATION] {col} has {nulls} nulls — dropping rows")
                df = df.dropna(subset=[col])

    # 3. Duplicate Customer_ID rows
    dups = df.duplicated(subset=["Customer_ID"], keep="first").sum()
    if dups:
        report["issues"].append(f"Customer_ID duplicates: {dups} removed")
        logger.warning(f"[VALIDATION] Removed {dups} duplicate Customer_ID rows")
        df = df.drop_duplicates(subset=["Customer_ID"], keep="first")

    # 4. Customer_ID must be positive integer
    df["Customer_ID"] = pd.to_numeric(df["Customer_ID"], errors="coerce")
    invalid_ids = df["Customer_ID"].isna() | (df["Customer_ID"] <= 0)
    if invalid_ids.any():
        report["issues"].append(f"Invalid Customer_ID: {invalid_ids.sum()} rows dropped")
        df = df[~invalid_ids]

    # 5. DOB — valid date
    df["DOB"] = pd.to_datetime(df["DOB"], errors="coerce")
    bad_dob = df["DOB"].isna().sum()
    if bad_dob:
        report["issues"].append(f"DOB unparseable: {bad_dob} rows dropped")
        df = df.dropna(subset=["DOB"])

    report["rows_out"] = len(df)
    if not report["issues"]:
        report["issues"].append("All checks passed.")
    return df, report


def validate_policies(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"table": "policies", "issues": [], "rows_in": len(df), "rows_out": None}

    required = ["Policy_Id", "Customer_ID", "Policy_Type_Id", "Policy_Type",
                "Premium_Amt", "Policy_Term", "Policy_Start_Dt", "Total_Policy_Amt"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        report["issues"].append(f"Missing columns: {missing_cols}")

    for col in ["Policy_Id", "Customer_ID", "Premium_Amt"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            nulls = df[col].isna().sum()
            if nulls:
                report["issues"].append(f"{col}: {nulls} non-numeric/null → dropped")
                df = df.dropna(subset=[col])

    # Premium must be > 0
    neg_prem = (df["Premium_Amt"] <= 0).sum()
    if neg_prem:
        report["issues"].append(f"Premium_Amt ≤ 0: {neg_prem} rows removed")
        df = df[df["Premium_Amt"] > 0]

    # Remove duplicate Policy_Id
    dups = df.duplicated(subset=["Policy_Id"], keep="first").sum()
    if dups:
        report["issues"].append(f"Policy_Id duplicates: {dups} removed")
        df = df.drop_duplicates(subset=["Policy_Id"], keep="first")

    # Validate dates
    for dc in ["Policy_Start_Dt", "Policy_End_Dt"]:
        if dc in df.columns:
            df[dc] = pd.to_datetime(df[dc], errors="coerce")

    # End date must be after start date
    if "Policy_Start_Dt" in df.columns and "Policy_End_Dt" in df.columns:
        bad_dates = (df["Policy_End_Dt"] < df["Policy_Start_Dt"]).sum()
        if bad_dates:
            report["issues"].append(f"End before start: {bad_dates} rows removed")
            df = df[df["Policy_End_Dt"] >= df["Policy_Start_Dt"]]

    report["rows_out"] = len(df)
    if not report["issues"]:
        report["issues"].append("All checks passed.")
    return df, report


def validate_address(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"table": "address", "issues": [], "rows_in": len(df), "rows_out": None}

    for col in ["Customer_ID", "Region", "Country"]:
        if col in df.columns:
            nulls = df[col].isna().sum()
            if nulls:
                report["issues"].append(f"{col}: {nulls} nulls → dropped")
                df = df.dropna(subset=[col])

    dups = df.duplicated(subset=["Customer_ID"], keep="first").sum()
    if dups:
        report["issues"].append(f"Customer_ID address duplicates: {dups} removed")
        df = df.drop_duplicates(subset=["Customer_ID"], keep="first")

    report["rows_out"] = len(df)
    if not report["issues"]:
        report["issues"].append("All checks passed.")
    return df, report


def validate_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"table": "transactions", "issues": [], "rows_in": len(df), "rows_out": None}

    for col in ["Policy_Id", "Customer_ID", "Premium_Amt", "Total_Policy_Amt"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            nulls = df[col].isna().sum()
            if nulls:
                report["issues"].append(f"{col}: {nulls} nulls/non-numeric → dropped")
                df = df.dropna(subset=[col])

    neg_prem = (df["Premium_Amt"] <= 0).sum()
    if neg_prem:
        report["issues"].append(f"Premium_Amt ≤ 0: {neg_prem} rows removed")
        df = df[df["Premium_Amt"] > 0]

    if "Actual_Premium_Paid_Dt" in df.columns:
        df["Actual_Premium_Paid_Dt"] = pd.to_datetime(
            df["Actual_Premium_Paid_Dt"], errors="coerce")

    report["rows_out"] = len(df)
    if not report["issues"]:
        report["issues"].append("All checks passed.")
    return df, report


def run_validation(data: dict) -> tuple[dict, list]:
    """
    data = {"customers": df, "policies": df, "address": df, "transactions": df}
    Returns cleaned data dict and list of reports.
    """
    cleaned = {}
    reports = []

    df_c, r = validate_customers(data["customers"].copy())
    cleaned["customers"] = df_c; reports.append(r)

    df_p, r = validate_policies(data["policies"].copy())
    cleaned["policies"] = df_p; reports.append(r)

    df_a, r = validate_address(data["address"].copy())
    cleaned["address"] = df_a; reports.append(r)

    df_t, r = validate_transactions(data["transactions"].copy())
    cleaned["transactions"] = df_t; reports.append(r)

    return cleaned, reports
