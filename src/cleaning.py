"""
Data Cleaning and Preprocessing Pipeline for RetailPulse.
Enforces rigorous audit logging of every record modification or exclusion,
handles cancellations and returns separately, preserves unidentified guest
transactions for sales analytics, and isolates customer-level datasets.
"""

from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np

from src.config import (
    COL_INVOICE,
    COL_STOCK,
    COL_DESC,
    COL_QTY,
    COL_DATE,
    COL_PRICE,
    COL_CUST,
    COL_COUNTRY,
    COL_LINE_REVENUE,
    COL_IS_GUEST,
    NON_PRODUCT_STOCK_CODES,
    GUEST_CUSTOMER_LABEL,
)


class CleaningAuditLogger:
    """Collects structured log events during the cleaning pipeline."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_step(
        self,
        step_number: int,
        step_name: str,
        action: str,
        reason: str,
        rows_before: int,
        rows_affected: int,
        rows_after: int,
        notes: Optional[str] = None,
    ) -> None:
        self.logs.append({
            "Step": step_number,
            "Stage": step_name,
            "Action": action,
            "Reason": reason,
            "Rows Before": rows_before,
            "Rows Affected": rows_affected,
            "Rows After": rows_after,
            "Notes": notes or "",
        })

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.logs)


def run_cleaning_pipeline(
    raw_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, CleaningAuditLogger, Dict[str, Any]]:
    """
    Executes the comprehensive RetailPulse cleaning pipeline.

    Returns:
        sales_clean_df: Positive sales transactions for business analytics.
        cancellations_df: Cancellation and return transactions.
        customer_df: Transactions with identified CustomerID for RFM and clustering.
        logger: Audit logger containing row counts and rationale per step.
        guest_metrics: Breakdown of guest vs identified revenue and volume.
    """
    logger = CleaningAuditLogger()
    df = raw_df.copy()
    initial_rows = len(df)

    logger.log_step(
        step_number=1,
        step_name="Raw Input Ingestion",
        action="Load dataset",
        reason="Baseline input verification",
        rows_before=initial_rows,
        rows_affected=0,
        rows_after=initial_rows,
        notes="Raw transaction records ingested.",
    )

    # 1. Date and Price Parsing & Missingness Validation
    n_before = len(df)
    # Ensure InvoiceDate is datetime
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
    # Ensure UnitPrice and Quantity are numeric
    df[COL_PRICE] = pd.to_numeric(df[COL_PRICE], errors="coerce")
    df[COL_QTY] = pd.to_numeric(df[COL_QTY], errors="coerce")

    invalid_date_or_price = df[COL_DATE].isna() | df[COL_PRICE].isna() | df[COL_QTY].isna()
    dropped_invalid_type = df[invalid_date_or_price]
    df = df[~invalid_date_or_price].copy()
    n_after = len(df)

    logger.log_step(
        step_number=2,
        step_name="Validate Critical Fields",
        action="Drop corrupted dates/prices/quantities",
        reason="Cannot calculate timing or financial values with missing date, price, or quantity",
        rows_before=n_before,
        rows_affected=len(dropped_invalid_type),
        rows_after=n_after,
        notes=f"Dropped {len(dropped_invalid_type)} records lacking valid InvoiceDate, UnitPrice, or Quantity.",
    )

    # 2. De-duplication Policy:
    # Exact duplicates across all attributes are logged and removed to prevent double-counting
    n_before = len(df)
    duplicates_mask = df.duplicated()
    dup_count = duplicates_mask.sum()
    df = df[~duplicates_mask].copy()
    n_after = len(df)

    logger.log_step(
        step_number=3,
        step_name="Deduplication",
        action="Drop identical duplicate rows",
        reason="Prevent double-counting identical transaction line items",
        rows_before=n_before,
        rows_affected=int(dup_count),
        rows_after=n_after,
        notes=f"Removed {dup_count} exact duplicate rows.",
    )

    # 3. Handle Cancellations and Negative Quantities
    # InvoiceNo starting with 'C' indicates cancellation/credit note.
    # Negative quantity also denotes returns.
    n_before = len(df)
    invoice_str = df[COL_INVOICE].astype(str).str.strip()
    is_cancelled_invoice = invoice_str.str.startswith(("C", "c"))
    is_negative_qty = df[COL_QTY] < 0
    cancellation_mask = is_cancelled_invoice | is_negative_qty

    cancellations_df = df[cancellation_mask].copy()
    sales_df = df[~cancellation_mask].copy()
    n_after = len(sales_df)

    logger.log_step(
        step_number=4,
        step_name="Isolate Cancellations & Returns",
        action="Segregate into cancellations dataframe",
        reason="Returns/cancellations must not be silently netted into gross revenue; kept separate",
        rows_before=n_before,
        rows_affected=len(cancellations_df),
        rows_after=n_after,
        notes=f"Isolated {len(cancellations_df)} return/cancellation transactions.",
    )

    # 4. Zero / Non-Positive Prices & Non-Product Stock Codes
    n_before = len(sales_df)
    stock_code_clean = sales_df[COL_STOCK].astype(str).str.strip().str.upper()
    is_non_product_code = stock_code_clean.isin({c.upper() for c in NON_PRODUCT_STOCK_CODES})
    is_zero_or_negative_price = sales_df[COL_PRICE] <= 0

    non_product_mask = is_non_product_code | is_zero_or_negative_price
    non_product_df = sales_df[non_product_mask].copy()
    sales_df = sales_df[~non_product_mask].copy()
    n_after = len(sales_df)

    logger.log_step(
        step_number=5,
        step_name="Filter Non-Product & Zero-Price Items",
        action="Exclude non-product fees/postage/bad prices from merchandise sales",
        reason="POST, D, M, Bank Charges, and zero prices distort product-level analytics and pricing metrics",
        rows_before=n_before,
        rows_affected=len(non_product_df),
        rows_after=n_after,
        notes=f"Excluded {len(non_product_df)} non-merchandise or zero-price records.",
    )

    # 5. Compute Line Revenue
    sales_df[COL_LINE_REVENUE] = sales_df[COL_QTY] * sales_df[COL_PRICE]
    if len(cancellations_df) > 0:
        cancellations_df[COL_LINE_REVENUE] = cancellations_df[COL_QTY] * cancellations_df[COL_PRICE]

    # Add temporal helper columns
    sales_df["Year"] = sales_df[COL_DATE].dt.year
    sales_df["Month"] = sales_df[COL_DATE].dt.month
    sales_df["YearMonth"] = sales_df[COL_DATE].dt.to_period("M").astype(str)
    sales_df["Date"] = sales_df[COL_DATE].dt.date
    sales_df["DayOfWeek"] = sales_df[COL_DATE].dt.day_name()
    sales_df["Hour"] = sales_df[COL_DATE].dt.hour

    # Clean description and string columns
    sales_df[COL_DESC] = sales_df[COL_DESC].fillna("Unknown Item").astype(str).str.strip()
    sales_df[COL_COUNTRY] = sales_df[COL_COUNTRY].fillna("Unspecified").astype(str).str.strip()

    # 6. CustomerID Handling:
    # Missing CustomerIDs are KEPT for sales analytics, marked as Guest / Unidentified.
    # Excluded from customer-level RFM and clustering.
    guest_mask = (
        sales_df[COL_CUST].isna()
        | (sales_df[COL_CUST].astype(str).str.strip().isin(["", "nan", "None", "NaN"]))
    )
    sales_df[COL_IS_GUEST] = guest_mask

    # Standardize CustomerID column for identified customers (integer/clean string)
    def clean_cust_id(val):
        if pd.isna(val) or str(val).strip() in ["", "nan", "None", "NaN"]:
            return GUEST_CUSTOMER_LABEL
        try:
            return str(int(float(val)))
        except (ValueError, TypeError):
            return str(val).strip()

    sales_df[COL_CUST] = sales_df[COL_CUST].apply(clean_cust_id)

    total_sales_value = float(sales_df[COL_LINE_REVENUE].sum())
    guest_sales_value = float(sales_df.loc[sales_df[COL_IS_GUEST], COL_LINE_REVENUE].sum())
    guest_rev_share = (guest_sales_value / total_sales_value * 100.0) if total_sales_value > 0 else 0.0
    guest_rows = int(guest_mask.sum())
    total_sales_rows = len(sales_df)
    guest_row_share = (guest_rows / total_sales_rows * 100.0) if total_sales_rows > 0 else 0.0

    logger.log_step(
        step_number=6,
        step_name="Guest Customer Flagging",
        action="Preserve guest sales, isolate from customer clustering",
        reason="Anonymous guest transactions drive valid revenue; dropping them understates sales",
        rows_before=total_sales_rows,
        rows_affected=guest_rows,
        rows_after=total_sales_rows,
        notes=(
            f"Preserved {guest_rows} guest rows ({guest_row_share:.2f}% of sales rows), "
            f"representing ${guest_sales_value:,.2f} ({guest_rev_share:.2f}% of positive sales value)."
        ),
    )

    # 7. Customer-level analysis dataset (Identified customers only)
    customer_df = sales_df[~sales_df[COL_IS_GUEST]].copy()

    logger.log_step(
        step_number=7,
        step_name="Customer Analysis Cohort",
        action="Create identified customer partition",
        reason="RFM and K-Means segmentation require consistent individual customer tracking",
        rows_before=total_sales_rows,
        rows_affected=len(customer_df),
        rows_after=len(customer_df),
        notes=f"{customer_df[COL_CUST].nunique()} unique identified customers in cohort.",
    )

    guest_metrics = {
        "total_sales_value": total_sales_value,
        "guest_sales_value": guest_sales_value,
        "guest_revenue_share_pct": guest_rev_share,
        "total_sales_rows": total_sales_rows,
        "guest_rows": guest_rows,
        "guest_row_share_pct": guest_row_share,
        "identified_customers_count": customer_df[COL_CUST].nunique(),
        "total_cancellations_count": len(cancellations_df),
        "cancellations_value": float(abs(cancellations_df[COL_LINE_REVENUE].sum())) if len(cancellations_df) > 0 else 0.0,
    }

    return sales_df, cancellations_df, customer_df, logger, guest_metrics
