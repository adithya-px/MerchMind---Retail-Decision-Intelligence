"""
Unit tests for sales analytics engine.
"""

import pytest
import pandas as pd
import numpy as np

from src.sales_analytics import (
    compute_kpis,
    filter_data,
    compute_monthly_trend,
    compute_pareto_concentration,
    what_drives_revenue_analysis,
    generate_sales_insights,
)
from src.config import GUEST_CUSTOMER_LABEL


@pytest.fixture
def clean_sales_sample():
    return pd.DataFrame([
        # Order 1: 2 lines by Cust 101, total = 30 + 20 = 50
        {"InvoiceNo": "1", "StockCode": "A", "Description": "Prod A", "Quantity": 3, "UnitPrice": 10.0, "LineRevenue": 30.0, "CustomerID": "101", "Country": "UK", "InvoiceDate": pd.to_datetime("2021-01-05"), "YearMonth": "2021-01", "Date": "2021-01-05", "DayOfWeek": "Tuesday", "Hour": 10},
        {"InvoiceNo": "1", "StockCode": "B", "Description": "Prod B", "Quantity": 2, "UnitPrice": 10.0, "LineRevenue": 20.0, "CustomerID": "101", "Country": "UK", "InvoiceDate": pd.to_datetime("2021-01-05"), "YearMonth": "2021-01", "Date": "2021-01-05", "DayOfWeek": "Tuesday", "Hour": 10},
        
        # Order 2: 1 line by Cust 102, total = 50
        {"InvoiceNo": "2", "StockCode": "A", "Description": "Prod A", "Quantity": 5, "UnitPrice": 10.0, "LineRevenue": 50.0, "CustomerID": "102", "Country": "France", "InvoiceDate": pd.to_datetime("2021-01-10"), "YearMonth": "2021-01", "Date": "2021-01-10", "DayOfWeek": "Sunday", "Hour": 14},
        
        # Order 3: 1 line by Cust 101, total = 100 in Feb
        {"InvoiceNo": "3", "StockCode": "C", "Description": "Prod C", "Quantity": 10, "UnitPrice": 10.0, "LineRevenue": 100.0, "CustomerID": "101", "Country": "UK", "InvoiceDate": pd.to_datetime("2021-02-15"), "YearMonth": "2021-02", "Date": "2021-02-15", "DayOfWeek": "Monday", "Hour": 9},
        
        # Order 4: Guest checkout, total = 40
        {"InvoiceNo": "4", "StockCode": "B", "Description": "Prod B", "Quantity": 4, "UnitPrice": 10.0, "LineRevenue": 40.0, "CustomerID": GUEST_CUSTOMER_LABEL, "Country": "UK", "InvoiceDate": pd.to_datetime("2021-02-20"), "YearMonth": "2021-02", "Date": "2021-02-20", "DayOfWeek": "Saturday", "Hour": 12},
    ])


def test_compute_kpis(clean_sales_sample):
    kpis = compute_kpis(clean_sales_sample)
    # Total revenue: 50 + 50 + 100 + 40 = 240
    assert kpis["total_positive_sales"] == 240.0
    # Distinct invoices: 4
    assert kpis["distinct_invoices"] == 4
    # Unique identified customers: Cust 101 and Cust 102 (guest excluded)
    assert kpis["unique_customers"] == 2
    # Distinct products: A, B, C = 3
    assert kpis["distinct_products"] == 3
    # AOV: 240 / 4 = 60.0
    assert kpis["avg_order_value"] == 60.0


def test_filter_data(clean_sales_sample):
    # Filter by country France
    france_df = filter_data(clean_sales_sample, countries=["France"])
    assert len(france_df) == 1
    assert france_df.iloc[0]["InvoiceNo"] == "2"

    # Filter by date range (January only)
    jan_df = filter_data(clean_sales_sample, start_date=pd.to_datetime("2021-01-01"), end_date=pd.to_datetime("2021-01-31"))
    assert len(jan_df) == 3
    assert set(jan_df["InvoiceNo"]) == {"1", "2"}


def test_pareto_concentration(clean_sales_sample):
    # Cust 101 total: 150 (75%), Cust 102 total: 50 (25%) out of 200 identified
    cust_df = clean_sales_sample[clean_sales_sample["CustomerID"] != GUEST_CUSTOMER_LABEL]
    pareto_df, top_20_share = compute_pareto_concentration(cust_df)
    assert len(pareto_df) == 2
    assert pareto_df.iloc[0]["CustomerID"] == "101"
    assert pareto_df.iloc[0]["CumulativeSharePct"] == 75.0


def test_what_drives_revenue_analysis(clean_sales_sample):
    drivers = what_drives_revenue_analysis(clean_sales_sample)
    assert drivers["top_country"] == "UK"
    # Jan sales: 100, Feb sales: 140 -> MoM delta = +40
    assert drivers["mom_delta"] == pytest.approx(40.0)
    assert drivers["mom_pct_change"] == pytest.approx(40.0)

