"""
etl/standardization.py
=======================
Data Standardization Stage
- Normalize region names → EAST / WEST / NORTH / SOUTH
- Normalize dates → YYYY-MM-DD (str)
- Normalize marital status → Single / Married / Divorced / Widowed
- Normalize gender → Male / Female
- Strip whitespace from all string columns
- Normalize policy term → Monthly / Quarterly / Annual
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)

REGION_MAP = {
    "east": "EAST", "e": "EAST", "ea": "EAST",
    "west": "WEST", "w": "WEST", "we": "WEST",
    "north": "NORTH", "n": "NORTH", "no": "NORTH",
    "south": "SOUTH", "s": "SOUTH", "so": "SOUTH",
}

MARITAL_MAP = {
    "single": "Single", "s": "Single", "unmarried": "Single",
    "married": "Married", "m": "Married", "wed": "Married",
    "divorced": "Divorced", "d": "Divorced", "div": "Divorced",
    "widowed": "Widowed", "w": "Widowed", "widow": "Widowed",
}

GENDER_MAP = {
    "male": "Male", "m": "Male",
    "female": "Female", "f": "Female",
}

TERM_MAP = {
    "monthly": "Monthly", "month": "Monthly", "mo": "Monthly",
    "quarterly": "Quarterly", "quarter": "Quarterly", "qtr": "Quarterly", "q": "Quarterly",
    "annual": "Annual", "annually": "Annual", "yearly": "Annual",
    "year": "Annual", "yr": "Annual",
}


def _normalize_col(series: pd.Series, mapping: dict, label: str) -> pd.Series:
    """Map a column using a lowercase lookup dict, log unknowns."""
    original = series.copy()
    result = series.astype(str).str.strip().str.lower().map(mapping)
    unknowns = result.isna() & original.notna() & (original.astype(str) != "nan")
    if unknowns.any():
        vals = original[unknowns].unique()
        logger.warning(f"[STANDARDIZE] {label}: unknown values {list(vals)[:5]} kept as-is")
        result[unknowns] = original[unknowns].astype(str).str.strip()
    return result


def _normalize_dates(series: pd.Series) -> pd.Series:
    """Parse dates and return YYYY-MM-DD strings; NaT → empty string."""
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d").fillna("")


def standardize_customers(df: pd.DataFrame) -> pd.DataFrame:
    # Strip all string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    df["Region"]         = _normalize_col(df["Region"],         REGION_MAP,  "Region")
    df["Marital_Status"] = _normalize_col(df["Marital_Status"], MARITAL_MAP, "Marital_Status")
    df["Gender"]         = _normalize_col(df["Gender"],         GENDER_MAP,  "Gender")

    # Name casing — title case
    for col in ["Customer_First_Name", "Customer_Last_Name"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    # Dates
    if "DOB" in df.columns:
        df["DOB"] = _normalize_dates(df["DOB"])
    for dc in ["Effective_Start_Dt", "Effective_End_Dt"]:
        if dc in df.columns:
            df[dc] = _normalize_dates(df[dc])

    logger.info(f"[STANDARDIZE] customers: {len(df)} rows standardized")
    return df


def standardize_policies(df: pd.DataFrame) -> pd.DataFrame:
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    df["Region"]      = _normalize_col(df["Region"],      REGION_MAP, "Region")
    df["Policy_Term"] = _normalize_col(df["Policy_Term"], TERM_MAP,   "Policy_Term")

    for dc in ["Policy_Start_Dt", "Policy_End_Dt",
               "Next_Premium_Dt", "Actual_Premium_Paid_Dt"]:
        if dc in df.columns:
            df[dc] = _normalize_dates(df[dc])

    df["Policy_Type"]      = df["Policy_Type"].astype(str).str.strip()
    df["Policy_Type_Desc"] = df["Policy_Type_Desc"].astype(str).str.strip()

    logger.info(f"[STANDARDIZE] policies: {len(df)} rows standardized")
    return df


def standardize_address(df: pd.DataFrame) -> pd.DataFrame:
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    df["Region"]  = _normalize_col(df["Region"], REGION_MAP, "Region")
    df["Country"] = df["Country"].astype(str).str.strip().str.title()
    df["State"]   = df["State"].astype(str).str.strip().str.title()
    df["City"]    = df["City"].astype(str).str.strip().str.title()

    logger.info(f"[STANDARDIZE] address: {len(df)} rows standardized")
    return df


def standardize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    df["Region"] = _normalize_col(df["Region"], REGION_MAP, "Region")

    for dc in ["Actual_Premium_Paid_Dt", "Next_Premium_Dt"]:
        if dc in df.columns:
            df[dc] = _normalize_dates(df[dc])

    logger.info(f"[STANDARDIZE] transactions: {len(df)} rows standardized")
    return df


def run_standardization(data: dict) -> dict:
    return {
        "customers":    standardize_customers(data["customers"].copy()),
        "policies":     standardize_policies(data["policies"].copy()),
        "address":      standardize_address(data["address"].copy()),
        "transactions": standardize_transactions(data["transactions"].copy()),
    }
