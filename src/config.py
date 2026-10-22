"""
Configuration module for MerchMind.
Stores column names, non-product stock codes, constants, and default parameters.
"""

from typing import List, Set, Tuple

# Required raw schema columns
REQUIRED_COLUMNS: List[str] = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

# Standard column mappings
COL_INVOICE = "InvoiceNo"
COL_STOCK = "StockCode"
COL_DESC = "Description"
COL_QTY = "Quantity"
COL_DATE = "InvoiceDate"
COL_PRICE = "UnitPrice"
COL_CUST = "CustomerID"
COL_COUNTRY = "Country"
COL_LINE_REVENUE = "LineRevenue"
COL_IS_GUEST = "IsGuest"
COL_IS_RETURN = "IsCancellation"

# Known non-product stock codes and fees to exclude from product analysis
NON_PRODUCT_STOCK_CODES: Set[str] = {
    "POST",           # Postage
    "D",              # Discount
    "M",              # Manual
    "BANK CHARGES",   # Bank fees
    "PADS",           # Pads to match all cushions
    "DOT",            # DOTCOM POSTAGE
    "CRUK",           # CRUK Commission
    "AMAZONFEE",      # Amazon fee
    "S",              # Samples
    "m",              # manual lowercase
    "gift_0001_10",   # Gift vouchers
    "gift_0001_20",
    "gift_0001_30",
    "gift_0001_40",
    "gift_0001_50",
    "TEST",           # Test entries
    "ADJUST",         # Adjustments
    "ADJUST2",
}

# Paths and cache settings
DEFAULT_RAW_CSV = "data/raw/Online Retail.csv"
DEFAULT_RAW_EXCEL = "data/raw/Online Retail.xlsx"
PROCESSED_DATA_DIR = "data/processed"

# ML & Customer Intelligence Defaults
RANDOM_SEED: int = 42
DEFAULT_K_CLUSTERS: int = 4
CANDIDATE_K_RANGE: Tuple[int, int] = (2, 8)

# Activity decline detection defaults
DEFAULT_RECENT_WINDOW_DAYS: int = 90
DEFAULT_PRIOR_WINDOW_DAYS: int = 90
MIN_TRANSACTIONS_FOR_DECLINE: int = 2
MIN_PAST_SPEND_FOR_DECLINE: float = 50.0

# Predictive analytics (churn / inactivity + spend) defaults
PREDICTIVE_LOOKBACK_DAYS: int = 90
PREDICTIVE_HORIZON_DAYS: int = 90
PREDICTIVE_N_TRAIN_CUTOFFS: int = 2
PREDICTIVE_TRAIN_CUTOFF_SPACING_DAYS: int = 30
PREDICTIVE_VALIDATION_FRACTION: float = 0.30
PREDICTIVE_MIN_CUSTOMERS: int = 50
PREDICTIVE_OUTREACH_PAYLOAD_LIMIT: int = 250
PREDICTIVE_CACHE_DIR: str = "data/processed/predictive_cache"

# Guest customer identifier
GUEST_CUSTOMER_LABEL: str = "Guest / Unidentified"
