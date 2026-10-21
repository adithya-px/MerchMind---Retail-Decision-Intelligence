"""
Unit tests for data loader: file formats, hashing, Parquet caching, and validation.
"""

import os
import io
import pytest
import pandas as pd
from src.data_loader import load_raw_data, compute_file_hash, standardize_columns, validate_schema


def test_compute_file_hash():
    data1 = b"Sample transaction data 1"
    data2 = b"Sample transaction data 2"
    h1 = compute_file_hash(data1)
    h2 = compute_file_hash(data2)
    assert len(h1) == 16
    assert h1 != h2
    assert h1 == compute_file_hash(data1)


def test_load_raw_data_from_csv_buffer(tmp_path):
    csv_content = (
        "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n"
        "536365,85123A,WHITE HANGING HEART T-LIGHT HOLDER,6,2010-12-01 08:26:00,2.55,17850,United Kingdom\n"
        "536365,71053,WHITE METAL LANTERN,6,2010-12-01 08:26:00,3.39,17850,United Kingdom\n"
    )
    buf = io.BytesIO(csv_content.encode("utf-8"))
    df, f_hash = load_raw_data(buf, file_name="test.csv", use_cache=True, processed_dir=str(tmp_path))
    
    assert len(df) == 2
    assert "InvoiceNo" in df.columns
    # Check cache parquet file created
    cached_file = tmp_path / f"raw_{f_hash}.parquet"
    assert cached_file.exists()
    
    # Second load should read from cache
    df_cached, f_hash_cached = load_raw_data(buf, file_name="test.csv", use_cache=True, processed_dir=str(tmp_path))
    assert len(df_cached) == 2
    assert f_hash == f_hash_cached


def test_load_raw_data_invalid_columns(tmp_path):
    csv_content = "InvoiceNo,Quantity,UnitPrice\n1001,5,10.0\n"
    buf = io.BytesIO(csv_content.encode("utf-8"))
    with pytest.raises(ValueError, match="Missing required column"):
        load_raw_data(buf, file_name="invalid.csv", use_cache=False, processed_dir=str(tmp_path))
