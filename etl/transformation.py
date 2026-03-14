"""
etl/transformation.py
=====================
Business Transformation Stage:
1. Late fee calculation  (Premium × 2%)
2. Installment count     (Monthly→12, Quarterly→4, Annual→1)
3. SCD handling          (Slowly Changing Dimensions for marital/policy changes)
4. Build dim_customer, dim_policy, dim_address, fact_transactions
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

LATE_FEE_RATE = 0.02   # 2% of premium

INSTALLMENT_MAP = {
    "Monthly":   12,
    "Quarterly":  4,
    "Annual":     1,
}


# ───────────────────────────────────────────────────────────────────
# 1. Late fee calculation
# ───────────────────────────────────────────────────────────────────
def compute_late_fees(transactions: pd.DataFrame,
                      policies: pd.DataFrame) -> pd.DataFrame:
    """
    If Actual_Premium_Paid_Dt > Next_Premium_Dt → late → add late fee.
    Late_Fee = Premium_Amt × LATE_FEE_RATE
    """
    df = transactions.copy()
    pol_map = policies[["Policy_Id", "Next_Premium_Dt", "Premium_Amt"]].copy()
    pol_map = pol_map.rename(columns={"Next_Premium_Dt": "Due_Dt",
                                       "Premium_Amt": "Pol_Premium"})

    df = df.merge(pol_map, on="Policy_Id", how="left")

    df["Actual_Premium_Paid_Dt"] = pd.to_datetime(df["Actual_Premium_Paid_Dt"], errors="coerce")
    df["Due_Dt"]                 = pd.to_datetime(df["Due_Dt"], errors="coerce")

    df["Is_Late"]  = df["Actual_Premium_Paid_Dt"] > df["Due_Dt"]
    df["Late_Fee"] = np.where(df["Is_Late"],
                              df["Premium_Amt"] * LATE_FEE_RATE, 0)
    df["Late_Fee"] = df["Late_Fee"].round(2)

    df = df.drop(columns=["Due_Dt", "Pol_Premium"], errors="ignore")
    late_count = df["Is_Late"].sum()
    logger.info(f"[TRANSFORM] Late fee: {late_count} late payments found, fee rate {LATE_FEE_RATE*100}%")
    return df


# ───────────────────────────────────────────────────────────────────
# 2. Installment count
# ───────────────────────────────────────────────────────────────────
def compute_installments(policies: pd.DataFrame) -> pd.DataFrame:
    df = policies.copy()
    df["Num_Installments"] = df["Policy_Term"].map(INSTALLMENT_MAP).fillna(1).astype(int)
    logger.info("[TRANSFORM] Installment counts computed")
    return df


# ───────────────────────────────────────────────────────────────────
# 3. SCD — policy change detection
# ───────────────────────────────────────────────────────────────────
def detect_policy_changes(prev_policies: pd.DataFrame,
                           curr_policies: pd.DataFrame) -> pd.DataFrame:
    """
    Compare previous day policies to current day.
    Returns rows where Policy_Type changed (SCD Type 2 pattern).
    """
    merged = curr_policies.merge(
        prev_policies[["Policy_Id", "Policy_Type_Id", "Policy_Type"]],
        on="Policy_Id", how="inner",
        suffixes=("_curr", "_prev")
    )
    changed = merged[merged["Policy_Type_Id_curr"] != merged["Policy_Type_Id_prev"]].copy()
    changed = changed.rename(columns={
        "Policy_Type_Id_curr":   "Current_Policy_Type_Id",
        "Policy_Type_curr":      "Current_Policy_Type",
        "Policy_Type_Id_prev":   "Previous_Policy_Type_Id",
        "Policy_Type_prev":      "Previous_Policy_Type",
    })
    logger.info(f"[TRANSFORM] Policy changes detected: {len(changed)} policies changed type")
    return changed


# ───────────────────────────────────────────────────────────────────
# 4. SCD — marital status change detection
# ───────────────────────────────────────────────────────────────────
def detect_marital_changes(all_customer_history: pd.DataFrame) -> pd.DataFrame:
    """
    From the full customer history (all days merged),
    find customers who have more than one distinct Marital_Status.
    Returns a dataframe showing each status + effective dates.
    """
    df = all_customer_history.copy()
    df = df.sort_values(["Customer_ID", "Effective_Start_Dt"])

    # Customers with multiple statuses
    cust_statuses = df.groupby("Customer_ID")["Marital_Status"].nunique()
    changed_ids   = cust_statuses[cust_statuses > 1].index

    changed_df = df[df["Customer_ID"].isin(changed_ids)].copy()
    logger.info(f"[TRANSFORM] Marital status changes: {len(changed_ids)} customers changed status")
    return changed_df


# ───────────────────────────────────────────────────────────────────
# 5. Build Dimensional Model
# ───────────────────────────────────────────────────────────────────
def build_dim_customer(customers_all: pd.DataFrame) -> pd.DataFrame:
    """
    dim_customer — SCD Type 2 columns included.
    Dedup based on Customer_ID + Effective_Start_Dt.
    """
    df = customers_all.copy()
    df = df.drop_duplicates(subset=["Customer_ID", "Effective_Start_Dt"], keep="last")
    df = df.sort_values(["Customer_ID", "Effective_Start_Dt"])

    # Surrogate key
    df = df.reset_index(drop=True)
    df.insert(0, "Customer_SK", range(1, len(df) + 1))

    # Customer full name
    df["Customer_Name"] = (df["Customer_Title"].fillna("") + " " +
                           df["Customer_First_Name"].fillna("") + " " +
                           df["Customer_Last_Name"].fillna("")).str.strip()

    logger.info(f"[TRANSFORM] dim_customer: {len(df)} rows built")
    return df


def build_dim_policy(policies_all: pd.DataFrame) -> pd.DataFrame:
    df = policies_all.copy()
    df = df.drop_duplicates(subset=["Policy_Id"], keep="last")
    df = df.reset_index(drop=True)
    df.insert(0, "Policy_SK", range(1, len(df) + 1))
    logger.info(f"[TRANSFORM] dim_policy: {len(df)} rows built")
    return df


def build_dim_address(address_all: pd.DataFrame) -> pd.DataFrame:
    df = address_all.copy()
    df = df.drop_duplicates(subset=["Customer_ID"], keep="last")
    df = df.reset_index(drop=True)
    df.insert(0, "Address_SK", range(1, len(df) + 1))
    logger.info(f"[TRANSFORM] dim_address: {len(df)} rows built")
    return df


def build_fact_transactions(transactions: pd.DataFrame,
                             dim_customer: pd.DataFrame,
                             dim_policy: pd.DataFrame,
                             dim_address: pd.DataFrame) -> pd.DataFrame:
    """
    fact_transactions — joins transaction data with surrogate keys.
    """
    df = transactions.copy()

    # Ensure consistent types for merge keys
    df["Customer_ID"] = df["Customer_ID"].astype(str)
    df["Policy_Id"]   = df["Policy_Id"].astype(str)

    cust_sk = dim_customer[["Customer_ID", "Customer_SK"]].drop_duplicates("Customer_ID").copy()
    pol_sk  = dim_policy[["Policy_Id",  "Policy_SK"]].drop_duplicates("Policy_Id").copy()
    addr_sk = dim_address[["Customer_ID", "Address_SK"]].drop_duplicates("Customer_ID").copy()

    cust_sk["Customer_ID"] = cust_sk["Customer_ID"].astype(str)
    pol_sk["Policy_Id"]    = pol_sk["Policy_Id"].astype(str)
    addr_sk["Customer_ID"] = addr_sk["Customer_ID"].astype(str)

    df = df.merge(cust_sk, on="Customer_ID", how="left")
    df = df.merge(pol_sk,  on="Policy_Id",   how="left")
    df = df.merge(addr_sk, on="Customer_ID", how="left")

    df = df.reset_index(drop=True)
    df.insert(0, "Transaction_SK", range(1, len(df) + 1))

    logger.info(f"[TRANSFORM] fact_transactions: {len(df)} rows built")
    return df


# ───────────────────────────────────────────────────────────────────
# Master runner
# ───────────────────────────────────────────────────────────────────
def run_transformation(standardized: dict,
                       prev_day_policies: pd.DataFrame = None) -> dict:
    """
    standardized: {"customers": df, "policies": df,
                   "address": df, "transactions": df}
    prev_day_policies: previous day's policy df for SCD detection
    Returns: {
        "dim_customer", "dim_policy", "dim_address",
        "fact_transactions", "policy_changes", "marital_changes"
    }
    """
    customers    = standardized["customers"]
    policies     = standardized["policies"]
    address      = standardized["address"]
    transactions = standardized["transactions"]

    # Compute business columns
    policies     = compute_installments(policies)
    transactions = compute_late_fees(transactions, policies)

    # Detect changes (SCD)
    policy_changes  = pd.DataFrame()
    marital_changes = pd.DataFrame()

    if prev_day_policies is not None and not prev_day_policies.empty:
        policy_changes = detect_policy_changes(prev_day_policies, policies)

    marital_changes = detect_marital_changes(customers)

    # Build dimensions
    dim_customer = build_dim_customer(customers)
    dim_policy   = build_dim_policy(policies)
    dim_address  = build_dim_address(address)

    # Build fact
    fact_transactions = build_fact_transactions(
        transactions, dim_customer, dim_policy, dim_address)

    return {
        "dim_customer":    dim_customer,
        "dim_policy":      dim_policy,
        "dim_address":     dim_address,
        "fact_transactions": fact_transactions,
        "policy_changes":  policy_changes,
        "marital_changes": marital_changes,
    }
