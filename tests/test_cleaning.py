"""
Unit tests for data loader and cleaning pipeline.
Uses synthetic test fixtures to test all edge cases deterministically.
"""

import pytest
import pandas as pd
import numpy as np

from src.data_loader import standardize_columns, validate_schema
from src.cleaning import run_cleaning_pipeline
from src.config import GUEST_CUSTOMER_LABEL


@pytest.fixture
def sample_raw_data():
    """Create a hand-checkable synthetic dataset with known properties."""
    return pd.DataFrame([
        # Standard positive sales (Customer 101)
        {"InvoiceNo": "1001", "StockCode": "ITEM_A", "Description": "Product A", "Quantity": 2, "InvoiceDate": "2021-01-10 10:00:00", "UnitPrice": 10.0, "CustomerID": 101, "Country": "UK"},
        {"InvoiceNo": "1001", "StockCode": "ITEM_B", "Description": "Product B", "Quantity": 1, "InvoiceDate": "2021-01-10 10:00:00", "UnitPrice": 20.0, "CustomerID": 101, "Country": "UK"},
        
        # Second invoice for Customer 101
        {"InvoiceNo": "1002", "StockCode": "ITEM_A", "Description": "Product A", "Quantity": 3, "InvoiceDate": "2021-01-15 11:00:00", "UnitPrice": 10.0, "CustomerID": 101, "Country": "UK"},
        
        # Exact duplicate of the row above (should be removed)
        {"InvoiceNo": "1002", "StockCode": "ITEM_A", "Description": "Product A", "Quantity": 3, "InvoiceDate": "2021-01-15 11:00:00", "UnitPrice": 10.0, "CustomerID": 101, "Country": "UK"},
        
        # Cancellation with 'C' prefix (Customer 101 returned 1 of Item A)
        {"InvoiceNo": "C1003", "StockCode": "ITEM_A", "Description": "Product A", "Quantity": -1, "InvoiceDate": "2021-01-16 12:00:00", "UnitPrice": 10.0, "CustomerID": 101, "Country": "UK"},
        
        # Return with negative quantity without 'C' prefix
        {"InvoiceNo": "1004", "StockCode": "ITEM_B", "Description": "Product B", "Quantity": -1, "InvoiceDate": "2021-01-17 12:00:00", "UnitPrice": 20.0, "CustomerID": 102, "Country": "France"},
        
        # Non-product stock codes (POST postage fee and BANK CHARGES)
        {"InvoiceNo": "1005", "StockCode": "POST", "Description": "POSTAGE", "Quantity": 1, "InvoiceDate": "2021-01-18 14:00:00", "UnitPrice": 15.0, "CustomerID": 102, "Country": "France"},
        {"InvoiceNo": "1006", "StockCode": "BANK CHARGES", "Description": "Bank Charges", "Quantity": 1, "InvoiceDate": "2021-01-18 15:00:00", "UnitPrice": 25.0, "CustomerID": 102, "Country": "France"},
        
        # Non-positive unit price (free sample or damaged)
        {"InvoiceNo": "1007", "StockCode": "ITEM_C", "Description": "Product C", "Quantity": 5, "InvoiceDate": "2021-01-19 10:00:00", "UnitPrice": 0.0, "CustomerID": 103, "Country": "Germany"},
        
        # Missing date
        {"InvoiceNo": "1008", "StockCode": "ITEM_D", "Description": "Product D", "Quantity": 1, "InvoiceDate": None, "UnitPrice": 5.0, "CustomerID": 103, "Country": "Germany"},
        
        # Missing CustomerID (Guest checkout, valid positive sale!)
        {"InvoiceNo": "1009", "StockCode": "ITEM_A", "Description": "Product A", "Quantity": 4, "InvoiceDate": "2021-01-20 16:00:00", "UnitPrice": 10.0, "CustomerID": np.nan, "Country": "UK"},
    ])


def test_schema_validation_success():
    df = pd.DataFrame(columns=["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"])
    validate_schema(df)  # Should not raise


def test_schema_validation_failure():
    df = pd.DataFrame(columns=["InvoiceNo", "Quantity", "InvoiceDate"])
    with pytest.raises(ValueError, match="Missing required column"):
        validate_schema(df)


def test_standardize_columns():
    df = pd.DataFrame(columns=["invoice_no", "Stock_Code", "Customer ID", "price", "qty", "description", "Country", "invoice_date"])
    std_df = standardize_columns(df)
    assert "InvoiceNo" in std_df.columns
    assert "StockCode" in std_df.columns
    assert "CustomerID" in std_df.columns
    assert "UnitPrice" in std_df.columns
    assert "Quantity" in std_df.columns
    assert "InvoiceDate" in std_df.columns


def test_cleaning_pipeline_positive_sales_and_revenue(sample_raw_data):
    sales_df, cancellations_df, customer_df, logger, guest_metrics = run_cleaning_pipeline(sample_raw_data)
    
    # Check that duplicate row was removed
    # Hand calculation:
    # 1. Invoice 1001: 2*10 + 1*20 = 40
    # 2. Invoice 1002: 3*10 = 30 (duplicate dropped)
    # 3. Guest Invoice 1009: 4*10 = 40
    # Total Positive Sales Value = 40 + 30 + 40 = 110.0
    assert float(sales_df["LineRevenue"].sum()) == 110.0
    assert guest_metrics["total_sales_value"] == 110.0


def test_cancellations_handling(sample_raw_data):
    sales_df, cancellations_df, customer_df, logger, guest_metrics = run_cleaning_pipeline(sample_raw_data)
    
    # Cancellations: C1003 (qty -1, price 10 -> -10) and 1004 (qty -1, price 20 -> -20)
    assert len(cancellations_df) == 2
    assert set(cancellations_df["InvoiceNo"]) == {"C1003", "1004"}
    assert "C1003" not in sales_df["InvoiceNo"].values
    assert "1004" not in sales_df["InvoiceNo"].values


def test_non_product_and_zero_price_exclusion(sample_raw_data):
    sales_df, cancellations_df, customer_df, logger, guest_metrics = run_cleaning_pipeline(sample_raw_data)
    
    # POST, BANK CHARGES, ITEM_C with price 0.0 must be excluded from positive merchandise sales
    assert "POST" not in sales_df["StockCode"].values
    assert "BANK CHARGES" not in sales_df["StockCode"].values
    assert "ITEM_C" not in sales_df["StockCode"].values


def test_missing_customer_id_retention(sample_raw_data):
    sales_df, cancellations_df, customer_df, logger, guest_metrics = run_cleaning_pipeline(sample_raw_data)
    
    # Sales dataframe MUST retain the guest sale (Invoice 1009)
    assert "1009" in sales_df["InvoiceNo"].values
    guest_rows = sales_df[sales_df["CustomerID"] == GUEST_CUSTOMER_LABEL]
    assert len(guest_rows) == 1
    assert float(guest_rows["LineRevenue"].sum()) == 40.0
    
    # Customer-level cohort MUST exclude guest customers
    assert "1009" not in customer_df["InvoiceNo"].values
    assert GUEST_CUSTOMER_LABEL not in customer_df["CustomerID"].values
    assert customer_df["CustomerID"].nunique() == 1  # Only Customer 101 left (102 was cancellations/fees, 103 had 0 price / bad date)
    
    # Guest revenue share: 40 / 110 = 36.36%
    assert round(guest_metrics["guest_revenue_share_pct"], 2) == 36.36


def test_cleaning_audit_logger(sample_raw_data):
    sales_df, cancellations_df, customer_df, logger, guest_metrics = run_cleaning_pipeline(sample_raw_data)
    log_df = logger.to_dataframe()
    
    assert len(log_df) == 7
    assert "Deduplication" in log_df["Stage"].values
    assert "Isolate Cancellations & Returns" in log_df["Stage"].values
    assert "Guest Customer Flagging" in log_df["Stage"].values
