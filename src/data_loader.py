"""
Data loader module for MerchMind.
Handles CSV and Excel file ingestion, column standardisation, validation,
and file-hash-keyed caching to Parquet in data/processed/.
"""

import os
import hashlib
import io
from pathlib import Path
from typing import Union, Tuple, Optional, Dict
import pandas as pd

from src.config import REQUIRED_COLUMNS, PROCESSED_DATA_DIR


# Flexible mapping for UCI Online Retail dataset variants
COLUMN_ALIASES: Dict[str, str] = {
    "invoiceno": "InvoiceNo",
    "invoice": "InvoiceNo",
    "invoice_no": "InvoiceNo",
    "stockcode": "StockCode",
    "stock_code": "StockCode",
    "description": "Description",
    "quantity": "Quantity",
    "qty": "Quantity",
    "invoicedate": "InvoiceDate",
    "invoice_date": "InvoiceDate",
    "unitprice": "UnitPrice",
    "unit_price": "UnitPrice",
    "price": "UnitPrice",
    "customerid": "CustomerID",
    "customer_id": "CustomerID",
    "customer id": "CustomerID",
    "country": "Country",
}


def compute_file_hash(source: Union[str, Path, io.BytesIO, bytes]) -> str:
    """Compute a SHA-256 hash of file content or buffer."""
    hasher = hashlib.sha256()
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
    elif isinstance(source, io.BytesIO):
        curr_pos = source.tell()
        source.seek(0)
        while chunk := source.read(65536):
            hasher.update(chunk)
        source.seek(curr_pos)
    elif isinstance(source, bytes):
        hasher.update(source)
    else:
        raise ValueError("Unsupported source type for hashing")
    return hasher.hexdigest()[:16]


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to the canonical schema using known aliases."""
    normalized_names = {}
    for col in df.columns:
        clean_key = str(col).strip().lower().replace(" ", "").replace("_", "")
        if clean_key in COLUMN_ALIASES:
            normalized_names[col] = COLUMN_ALIASES[clean_key]
        else:
            # Fallback direct match if trimmed
            for req in REQUIRED_COLUMNS:
                if str(col).strip().lower() == req.lower():
                    normalized_names[col] = req
                    break
    return df.rename(columns=normalized_names)


def validate_schema(df: pd.DataFrame) -> None:
    """
    Validate that required columns are present in the dataframe.
    Raises ValueError with actionable details if invalid.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Invalid dataset schema! Missing required column(s): {', '.join(missing)}. "
            f"Expected all of: {', '.join(REQUIRED_COLUMNS)}."
        )


def load_raw_data(
    source: Union[str, Path, io.BytesIO, bytes],
    file_name: Optional[str] = None,
    use_cache: bool = True,
    processed_dir: str = PROCESSED_DATA_DIR,
) -> Tuple[pd.DataFrame, str]:
    """
    Loads raw transaction data from CSV or Excel file / buffer.
    Utilizes Parquet caching keyed by file hash to avoid slow repeated Excel parsing.

    Parameters:
        source: Filepath, bytes, or BytesIO buffer.
        file_name: Optional filename for format inspection.
        use_cache: Whether to read/write from data/processed cache.
        processed_dir: Directory where cache parquets reside.

    Returns:
        (standardized_raw_df, file_hash)
    """
    file_hash = compute_file_hash(source)
    os.makedirs(processed_dir, exist_ok=True)
    cache_path = os.path.join(processed_dir, f"raw_{file_hash}.parquet")

    if use_cache and os.path.exists(cache_path):
        try:
            cached_df = pd.read_parquet(cache_path)
            validate_schema(cached_df)
            return cached_df, file_hash
        except Exception:
            # If cache read fails, re-parse source
            pass

    # Determine file format
    fmt = "csv"
    if file_name:
        fn_lower = file_name.lower()
        if fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls"):
            fmt = "excel"
    elif isinstance(source, (str, Path)):
        src_lower = str(source).lower()
        if src_lower.endswith(".xlsx") or src_lower.endswith(".xls"):
            fmt = "excel"

    # Read data
    if fmt == "excel":
        df = pd.read_excel(source, engine="openpyxl")
    else:
        # CSV reader with dtype hints to avoid warnings
        if isinstance(source, (io.BytesIO, bytes)):
            if isinstance(source, bytes):
                source = io.BytesIO(source)
            curr_pos = source.tell()
            source.seek(0)
            df = pd.read_csv(source, encoding="utf-8", low_memory=False)
            source.seek(curr_pos)
        else:
            df = pd.read_csv(source, encoding="utf-8", low_memory=False)

    df = standardize_columns(df)
    validate_schema(df)

    # Save to cache
    if use_cache:
        try:
            # Ensure CustomerID is stored cleanly
            save_df = df.copy()
            save_df.to_parquet(cache_path, index=False)
        except Exception:
            pass

    return df, file_hash
